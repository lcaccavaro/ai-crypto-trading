"""
Data quality reporter.

Aggregates per-dataset validation results into a run-level quality report.

Output files (per research run):
    results/<run_id>/data_quality_report.json    machine-readable
    results/<run_id>/data_quality_report.csv     spreadsheet-friendly
    results/<run_id>/dataset_manifest.json       dataset inventory

The quality report is the final word on what was downloaded and whether
it meets research quality standards.

Quality status rules:
    PASS     → all validators passed, dataset is research-ready
    WARNING  → missing candles detected; dataset usable with awareness
    FAIL     → OHLC violations, duplicates, nulls, or timestamp errors;
                dataset MUST NOT be used for research
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from crypto_research.data.metadata import DatasetMetadata
from crypto_research.data.validators import DatasetValidationSummary, ValidationStatus
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)

STATUS_SYMBOL = {
    ValidationStatus.PASS: "✅ PASS",
    ValidationStatus.WARNING: "⚠️  WARN",
    ValidationStatus.FAIL: "❌ FAIL",
}


class DataQualityReporter:
    """
    Collects validation summaries and generates a consolidated quality report.

    Usage:
        reporter = DataQualityReporter(run_dir=Path("results/RUN_..."))
        reporter.add(validation_summary, dataset_metadata)
        ...
        reporter.finalize()   # writes all output files + prints table
    """

    def __init__(self, run_dir: Path) -> None:
        self._run_dir = run_dir
        self._entries: list[dict] = []

    def add(
        self,
        summary: DatasetValidationSummary,
        metadata: Optional[DatasetMetadata] = None,
    ) -> None:
        """
        Register a validation result for one (symbol, timeframe) dataset.

        Args:
            summary:  DatasetValidationSummary from run_validation_pipeline().
            metadata: Optional DatasetMetadata for this dataset.
        """
        entry = {
            "symbol": summary.symbol,
            "timeframe": summary.timeframe,
            "row_count": summary.row_count,
            "status": summary.overall_status.value,
            "duplicate_count": summary.get_stat("duplicate_count", 0),
            "missing_count": summary.get_stat("missing_count", 0),
            "invalid_ohlc_count": summary.get_stat("invalid_count", 0),
            "null_count": summary.get_stat("total_null_count", 0),
            "order_errors": summary.get_stat("order_errors", 0),
            "issues": summary.all_issues,
            "dataset_id": metadata.dataset_id if metadata else None,
            "actual_start": metadata.actual_start if metadata else None,
            "actual_end": metadata.actual_end if metadata else None,
        }
        self._entries.append(entry)
        logger.info(
            "Quality entry recorded",
            symbol=summary.symbol,
            timeframe=summary.timeframe,
            status=summary.overall_status.value,
        )

    def finalize(self) -> dict:
        """
        Write all quality report files and print the summary table to stdout.

        Returns:
            The complete quality report dict (same as what's written to JSON).
        """
        self._run_dir.mkdir(parents=True, exist_ok=True)

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_datasets": len(self._entries),
            "passed": sum(1 for e in self._entries if e["status"] == "PASS"),
            "warnings": sum(1 for e in self._entries if e["status"] == "WARNING"),
            "failed": sum(1 for e in self._entries if e["status"] == "FAIL"),
            "datasets": self._entries,
        }

        # JSON
        json_path = self._run_dir / "data_quality_report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)

        # CSV
        csv_path = self._run_dir / "data_quality_report.csv"
        flat_columns = [
            "symbol", "timeframe", "row_count", "status",
            "duplicate_count", "missing_count", "invalid_ohlc_count",
            "null_count", "order_errors", "actual_start", "actual_end",
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=flat_columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(self._entries)

        # Print summary table
        self._print_table(report)

        logger.info(
            "Quality report written",
            json_path=str(json_path),
            csv_path=str(csv_path),
            total=report["total_datasets"],
            passed=report["passed"],
            warnings=report["warnings"],
            failed=report["failed"],
        )
        return report

    def generate_manifest(
        self,
        store_datasets: list[dict],
        run_id: str,
    ) -> Path:
        """
        Generate a machine-readable dataset manifest.

        The manifest describes every dataset that exists on disk,
        enriched with quality status from this report run.

        Args:
            store_datasets: Output of ParquetDataStore.list_datasets().
            run_id:         The current research run ID.

        Returns:
            Path to the written manifest file.
        """
        # Build status lookup from quality entries
        status_lookup = {
            (e["symbol"], e["timeframe"]): e["status"]
            for e in self._entries
        }

        manifest_entries = []
        for ds in store_datasets:
            key = (ds["symbol"], ds["timeframe"])
            manifest_entries.append({
                **ds,
                "quality_status": status_lookup.get(key, "UNKNOWN"),
                "last_run_id": run_id,
            })

        manifest = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "dataset_count": len(manifest_entries),
            "datasets": manifest_entries,
        }

        # Write to both results dir and data/metadata dir
        results_manifest = self._run_dir / "dataset_manifest.json"
        with open(results_manifest, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, default=str)

        logger.info(
            "Dataset manifest written",
            path=str(results_manifest),
            count=len(manifest_entries),
        )
        return results_manifest

    def _print_table(self, report: dict) -> None:
        """Print a human-readable quality summary table."""
        print()
        print("=" * 75)
        print("  DATA QUALITY REPORT")
        print("=" * 75)
        print(f"  {'Symbol':<12} {'TF':<6} {'Rows':>8}  {'Dups':>5}  {'Gaps':>6}  {'Invalid':>7}  {'Nulls':>5}  Status")
        print("-" * 75)
        for e in self._entries:
            status_str = STATUS_SYMBOL.get(
                ValidationStatus(e["status"]),
                e["status"]
            )
            print(
                f"  {e['symbol']:<12} {e['timeframe']:<6} "
                f"{e['row_count']:>8,}  "
                f"{e['duplicate_count']:>5}  "
                f"{e['missing_count']:>6}  "
                f"{e['invalid_ohlc_count']:>7}  "
                f"{e['null_count']:>5}  "
                f"{status_str}"
            )
        print("-" * 75)
        print(
            f"  Total: {report['total_datasets']} datasets | "
            f"✅ {report['passed']} PASS | "
            f"⚠️  {report['warnings']} WARN | "
            f"❌ {report['failed']} FAIL"
        )
        print("=" * 75)
        print()

        # List any issues explicitly — no silencing
        for e in self._entries:
            if e["issues"]:
                print(f"  Issues for {e['symbol']}/{e['timeframe']}:")
                for issue in e["issues"]:
                    print(f"    ▸ {issue}")
        if any(e["issues"] for e in self._entries):
            print()
