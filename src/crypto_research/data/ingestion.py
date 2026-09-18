"""
Data ingestion pipeline for Binance Futures historical OHLCV data.

Orchestrates the full download, conversion, validation, and storage flow:

    BinanceFuturesClient.fetch_klines()
            ↓ raw klines (list[list])
    ParquetDataStore.save_raw()          ← preserve audit record
            ↓
    ParquetDataStore.raw_klines_to_dataframe()
            ↓ canonical DataFrame
    run_validation_pipeline()
            ↓ DatasetValidationSummary
    ParquetDataStore.save()              ← canonical Parquet
            ↓
    DatasetMetadata.save()               ← provenance record
            ↓
    DataQualityReporter.add()
            ↓
    DataQualityReporter.finalize()       ← quality report files + table

Design rules:
    - No silent fallbacks at any stage.
    - If ONE symbol/timeframe fails, the error is reported.
      Other symbols/timeframes continue and are reported accurately.
    - A partial result is classified as PARTIAL, not COMPLETE.
    - No fake data is used under any circumstance.
    - Raw data is always preserved before any transformation.

Command-line usage:
    python3 -m crypto_research.data.ingestion
    # Reads config.yaml, downloads all configured assets/timeframes.
    # Use --demo for a short-range validation run (recommended for first run).
    # Omit --demo (or set use_full_range=True) to download the full configured range.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

from crypto_research.config.loader import find_project_root, load_config
from crypto_research.config.schema import ProjectConfiguration
from crypto_research.core.exceptions import DataIngestionError, DataIntegrityError
from crypto_research.data.binance_client import BinanceFuturesClient
from crypto_research.data.catalog import DataCatalog
from crypto_research.data.metadata import DatasetMetadata
from crypto_research.data.quality import DataQualityReporter
from crypto_research.data.store import ParquetDataStore
from crypto_research.data.validators import ValidationStatus, run_validation_pipeline
from crypto_research.research.run_manager import RunManager
from crypto_research.utils.environment import get_full_environment_info
from crypto_research.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Demo range
# ---------------------------------------------------------------------------

# For initial validation: download the last N days only.
# ⚠️  TO DOWNLOAD THE FULL RANGE:
#     Set use_full_range=True in DataIngestionPipeline.run()
#     or run without --demo flag from the command line.
#     The full range is configured by data.start_date / data.end_date in config.yaml.
DEMO_DAYS = 30


@dataclass
class IngestionResult:
    """Result of ingesting one (symbol, timeframe) dataset."""

    symbol: str
    timeframe: str
    status: str  # "SUCCESS", "PARTIAL", "FAILED"
    rows_downloaded: int = 0
    actual_start: Optional[str] = None
    actual_end: Optional[str] = None
    error: Optional[str] = None
    quality_status: Optional[str] = None


@dataclass
class PipelineResult:
    """Aggregated result for the full ingestion run."""

    run_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    results: list[IngestionResult] = field(default_factory=list)
    quality_report_path: Optional[str] = None
    manifest_path: Optional[str] = None

    @property
    def succeeded(self) -> list[IngestionResult]:
        return [r for r in self.results if r.status == "SUCCESS"]

    @property
    def failed(self) -> list[IngestionResult]:
        return [r for r in self.results if r.status == "FAILED"]

    @property
    def total(self) -> int:
        return len(self.results)

    def print_summary(self) -> None:
        """Print a final ingestion summary to stdout."""
        elapsed = (self.end_time - self.start_time).total_seconds() if self.end_time else 0
        print()
        print("=" * 60)
        print("  INGESTION PIPELINE SUMMARY")
        print("=" * 60)
        print(f"  Run ID    : {self.run_id}")
        print(f"  Elapsed   : {elapsed:.1f}s")
        print(f"  Total     : {self.total}")
        print(f"  Succeeded : {len(self.succeeded)}")
        print(f"  Failed    : {len(self.failed)}")
        print()
        for r in self.results:
            icon = "✅" if r.status == "SUCCESS" else "❌"
            rows = f"{r.rows_downloaded:,}" if r.rows_downloaded else "—"
            err = f"  ERROR: {r.error}" if r.error else ""
            print(f"  {icon} {r.symbol:<12} {r.timeframe:<5}  {rows:>8} rows{err}")
        print("=" * 60)

        if self.failed:
            print()
            print("  ❌ FAILED DATASETS (must be investigated — no fake data was used):")
            for r in self.failed:
                print(f"     {r.symbol}/{r.timeframe}: {r.error}")
            print()


class DataIngestionPipeline:
    """
    Orchestrates Binance Futures historical data download for all
    configured (symbol, timeframe) pairs.

    Args:
        config:       Validated ProjectConfiguration from load_config().
        project_root: Path to the project root directory.
    """

    def __init__(
        self,
        config: ProjectConfiguration,
        project_root: Optional[Path] = None,
    ) -> None:
        self._config = config
        self._project_root = project_root or find_project_root()
        self._data_cfg = config.data

        # Resolve storage paths relative to project root
        self._processed_dir = self._project_root / self._data_cfg.processed_dir
        self._raw_dir = self._project_root / self._data_cfg.raw_dir
        self._metadata_dir = self._project_root / self._data_cfg.metadata_dir

        self._store = ParquetDataStore(
            processed_dir=self._processed_dir,
            raw_dir=self._raw_dir,
        )
        self._client = BinanceFuturesClient(
            request_delay_ms=self._data_cfg.request_delay_ms,
            max_retries=self._data_cfg.max_retries,
            retry_delay_s=self._data_cfg.retry_delay_s,
        )
        self._catalog = DataCatalog(
            processed_dir=self._processed_dir,
            raw_dir=self._raw_dir,
            metadata_dir=self._metadata_dir,
            market_type=self._data_cfg.market_type,
        )

    def run(
        self,
        use_full_range: bool = False,
        run_id: Optional[str] = None,
        run_dir: Optional[Path] = None,
    ) -> PipelineResult:
        """
        Execute the full ingestion pipeline for all configured assets/timeframes.

        Args:
            use_full_range: If True, use config start_date/end_date (full research range).
                            If False (default), use the last DEMO_DAYS days only.
                            See DEMO_DAYS constant and config.yaml comments.
            run_id:         Optional external run ID (from RunManager).
            run_dir:        Optional run directory for quality report output.

        Returns:
            PipelineResult with per-dataset results and aggregate stats.
        """
        start_time = datetime.now(timezone.utc)

        # Determine date range
        if use_full_range:
            period_start = datetime.fromisoformat(self._data_cfg.start_date).replace(
                tzinfo=timezone.utc
            )
            period_end = datetime.fromisoformat(self._data_cfg.end_date).replace(
                tzinfo=timezone.utc
            )
            range_label = f"FULL RANGE: {self._data_cfg.start_date} → {self._data_cfg.end_date}"
        else:
            period_end = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            period_start = period_end - timedelta(days=DEMO_DAYS)
            range_label = f"DEMO RANGE: last {DEMO_DAYS} days"

        logger.info(
            "Ingestion pipeline starting",
            mode="full" if use_full_range else "demo",
            start=period_start.isoformat(),
            end=period_end.isoformat(),
            assets=self._config.assets,
            timeframes=self._config.timeframes,
        )

        print(f"\n  📥 Binance Futures Data Ingestion")
        print(f"  Market type : {self._data_cfg.market_type}")
        print(f"  Range       : {range_label}")
        print(f"  Assets      : {', '.join(self._config.assets)}")
        print(f"  Timeframes  : {', '.join(self._config.timeframes)}")
        print()

        # Verify connectivity before starting
        self._client.ping()
        logger.info("Binance Futures API connectivity confirmed")

        # Set up run artifacts
        if run_dir is None:
            run_dir = self._project_root / "results" / (run_id or "INGESTION")
        run_dir.mkdir(parents=True, exist_ok=True)

        reporter = DataQualityReporter(run_dir=run_dir)
        pipeline_result = PipelineResult(
            run_id=run_id or "standalone",
            start_time=start_time,
        )

        # Process each (symbol, timeframe) pair
        for symbol in self._config.assets:
            for timeframe in self._config.timeframes:
                result = self._ingest_one(
                    symbol=symbol,
                    timeframe=timeframe,
                    period_start=period_start,
                    period_end=period_end,
                    run_id=run_id or "standalone",
                    reporter=reporter,
                )
                pipeline_result.results.append(result)

        # Finalize quality report
        quality_report = reporter.finalize()
        pipeline_result.quality_report_path = str(run_dir / "data_quality_report.json")

        # Update global manifest
        manifest_path = self._catalog.update_manifest(run_id or "standalone")
        # Also copy manifest to run dir
        import shutil
        run_manifest = run_dir / "dataset_manifest.json"
        shutil.copy2(str(manifest_path), str(run_manifest))
        pipeline_result.manifest_path = str(run_manifest)

        pipeline_result.end_time = datetime.now(timezone.utc)
        pipeline_result.print_summary()

        return pipeline_result

    def _ingest_one(
        self,
        symbol: str,
        timeframe: str,
        period_start: datetime,
        period_end: datetime,
        run_id: str,
        reporter: DataQualityReporter,
    ) -> IngestionResult:
        """
        Download, validate, and store one (symbol, timeframe) dataset.

        If download fails: the error is recorded and the method returns
        a FAILED result. Execution continues for other pairs.
        """
        label = f"{symbol}/{timeframe}"
        print(f"  ⬇️  Downloading {label} ...")

        try:
            # Download all pages
            all_klines = self._download_all_pages(symbol, timeframe, period_start, period_end)

            if not all_klines:
                # No data returned — may be pre-listing. Record accurately.
                result = IngestionResult(
                    symbol=symbol,
                    timeframe=timeframe,
                    status="SUCCESS",
                    rows_downloaded=0,
                    error="No candles returned by Binance — symbol may not have existed "
                          "for this date range.",
                )
                # Still add to quality report with WARNING
                from crypto_research.data.validators import DatasetValidationSummary, ValidationResult, ValidationStatus
                empty_summary = DatasetValidationSummary(
                    symbol=symbol,
                    timeframe=timeframe,
                    row_count=0,
                    results=[ValidationResult(
                        validator_name="ingestion",
                        status=ValidationStatus.WARNING,
                        issues=["No candles returned by Binance API for the requested range."],
                    )],
                )
                reporter.add(empty_summary)
                print(f"  ⚠️  {label}: No data returned (pre-listing or invalid range)")
                return result

            # Convert to canonical DataFrame
            df = self._store.raw_klines_to_dataframe(all_klines, symbol, timeframe)

            actual_start = df["timestamp"].iloc[0].isoformat() if not df.empty else None
            actual_end = df["timestamp"].iloc[-1].isoformat() if not df.empty else None

            print(f"  ✅ {label}: {len(df):,} candles  [{actual_start[:10]} → {actual_end[:10]}]")

            # Validate
            validation_summary = run_validation_pipeline(df, symbol, timeframe)

            # Save canonical Parquet
            parquet_path = self._store.save(
                df=df,
                symbol=symbol,
                timeframe=timeframe,
                market_type=self._data_cfg.market_type,
                schema_version=self._data_cfg.schema_version,
            )

            # Compute checksum
            data_version = DatasetMetadata.compute_file_checksum(parquet_path)

            # Gather environment info for metadata
            env_info = get_full_environment_info()

            # Build and save dataset metadata
            metadata = DatasetMetadata(
                dataset_id=DatasetMetadata.make_dataset_id(
                    symbol, timeframe, self._data_cfg.market_type
                ),
                symbol=symbol,
                market_type=self._data_cfg.market_type,
                timeframe=timeframe,
                data_source="binance",
                source_endpoint="https://fapi.binance.com/fapi/v1/klines",
                requested_start=period_start.isoformat(),
                requested_end=period_end.isoformat(),
                actual_start=actual_start,
                actual_end=actual_end,
                download_timestamp=DatasetMetadata.now_utc(),
                run_id=run_id,
                git_commit=env_info.get("git_commit", "unavailable"),
                code_version=env_info.get("package_versions", {}).get(
                    "crypto-research", "unknown"
                ),
                row_count=len(df),
                schema_version=self._data_cfg.schema_version,
                data_version=data_version,
                quality_status=validation_summary.overall_status.value,
                quality_issues=validation_summary.all_issues,
                missing_candles=validation_summary.get_stat("missing_count", 0),
                duplicate_count=validation_summary.get_stat("duplicate_count", 0),
                invalid_ohlc_count=validation_summary.get_stat("invalid_count", 0),
                null_count=validation_summary.get_stat("total_null_count", 0),
            )
            meta_path = parquet_path.parent / f"{symbol}_{timeframe}_metadata.json"
            metadata.save(meta_path)

            reporter.add(validation_summary, metadata)

            return IngestionResult(
                symbol=symbol,
                timeframe=timeframe,
                status="SUCCESS",
                rows_downloaded=len(df),
                actual_start=actual_start,
                actual_end=actual_end,
                quality_status=validation_summary.overall_status.value,
            )

        except DataIngestionError as exc:
            error_msg = str(exc)
            logger.error(
                "Ingestion failed",
                symbol=symbol,
                timeframe=timeframe,
                error=error_msg,
            )
            print(f"  ❌ {label}: FAILED — {error_msg}")

            # Record FAIL in quality report — no fake data
            from crypto_research.data.validators import DatasetValidationSummary, ValidationResult, ValidationStatus
            fail_summary = DatasetValidationSummary(
                symbol=symbol,
                timeframe=timeframe,
                row_count=0,
                results=[ValidationResult(
                    validator_name="ingestion",
                    status=ValidationStatus.FAIL,
                    issues=[f"Download failed: {error_msg}"],
                )],
            )
            reporter.add(fail_summary)

            return IngestionResult(
                symbol=symbol,
                timeframe=timeframe,
                status="FAILED",
                error=error_msg,
            )

        except Exception as exc:
            error_msg = f"Unexpected error: {type(exc).__name__}: {exc}"
            logger.exception("Unexpected ingestion error", symbol=symbol, timeframe=timeframe)
            print(f"  ❌ {label}: UNEXPECTED ERROR — {error_msg}")

            from crypto_research.data.validators import DatasetValidationSummary, ValidationResult, ValidationStatus
            fail_summary = DatasetValidationSummary(
                symbol=symbol,
                timeframe=timeframe,
                row_count=0,
                results=[ValidationResult(
                    validator_name="ingestion",
                    status=ValidationStatus.FAIL,
                    issues=[error_msg],
                )],
            )
            reporter.add(fail_summary)

            return IngestionResult(
                symbol=symbol,
                timeframe=timeframe,
                status="FAILED",
                error=error_msg,
            )

    def _download_all_pages(
        self,
        symbol: str,
        timeframe: str,
        period_start: datetime,
        period_end: datetime,
    ) -> list:
        """
        Page through the Binance klines API to download the full date range.

        Binance returns at most 1500 candles per request. For large ranges,
        multiple requests are required with pagination via startTime.

        Args:
            symbol:       Trading pair.
            timeframe:    Candle interval.
            period_start: Start of desired range (UTC, inclusive).
            period_end:   End of desired range (UTC, exclusive).

        Returns:
            Concatenated list of all raw klines.
        """
        start_ms = int(period_start.timestamp() * 1000)
        end_ms = int(period_end.timestamp() * 1000)

        all_klines: list = []
        current_start_ms = start_ms
        batch_num = 0

        while current_start_ms < end_ms:
            batch_num += 1
            batch = self._client.fetch_klines(
                symbol=symbol,
                interval=timeframe,
                start_ms=current_start_ms,
                end_ms=end_ms,
            )

            if not batch:
                break  # No more data available

            # Save raw batch for auditability
            self._store.save_raw(
                raw_klines=batch,
                symbol=symbol,
                timeframe=timeframe,
                market_type=self._data_cfg.market_type,
                batch_start_ms=current_start_ms,
            )

            all_klines.extend(batch)

            # Advance cursor: next batch starts after the last candle's open time
            last_open_time_ms = batch[-1][0]
            current_start_ms = last_open_time_ms + 1  # +1ms to avoid overlap

            logger.debug(
                "Batch downloaded",
                symbol=symbol,
                timeframe=timeframe,
                batch=batch_num,
                rows=len(batch),
                total=len(all_klines),
            )

            # Safety: if batch filled exactly to limit, there may be more
            if len(batch) < 1500:
                break  # Binance returned less than max → we've reached the end

        return all_klines


# ---------------------------------------------------------------------------
# Command-line entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the ingestion pipeline from the command line."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Binance Futures historical data ingestion pipeline"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        default=False,
        help=(
            f"Download only the last {DEMO_DAYS} days (fast validation mode). "
            "Omit this flag to download the full range from config.yaml."
        ),
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to config.yaml (default: auto-discovered from project root)",
    )
    args = parser.parse_args()

    project_root = find_project_root()
    config_path = Path(args.config) if args.config else project_root / "config" / "config.yaml"
    config = load_config(config_path)

    # Set up research run
    run_manager = RunManager()
    research_run = run_manager.create_run(config, config_path=config_path)
    run_dir = Path(research_run.run_directory)
    log_dir = run_dir / "logs"

    setup_logging(
        run_id=research_run.run_id,
        log_dir=log_dir,
        level=config.logging.level,
        format=config.logging.format,
    )

    logger.info(
        "Ingestion run started",
        run_id=research_run.run_id,
        mode="demo" if args.demo else "full",
    )

    pipeline = DataIngestionPipeline(config=config, project_root=project_root)
    result = pipeline.run(
        use_full_range=not args.demo,
        run_id=research_run.run_id,
        run_dir=run_dir,
    )

    if result.failed:
        print(f"\n⚠️  {len(result.failed)} dataset(s) FAILED. See quality report for details.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
