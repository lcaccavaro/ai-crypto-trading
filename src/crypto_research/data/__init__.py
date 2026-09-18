"""
Data layer public API.

Provides clean imports for the data layer components implemented in Prompt 02.

Usage:
    from crypto_research.data import DataCatalog, DataIngestionPipeline
    from crypto_research.data import BinanceFuturesClient, BinanceDataProvider
"""

from crypto_research.data.binance_client import BinanceFuturesClient
from crypto_research.data.binance_provider import BinanceDataProvider
from crypto_research.data.catalog import DataCatalog, DatasetInfo
from crypto_research.data.ingestion import DataIngestionPipeline, IngestionResult, PipelineResult
from crypto_research.data.interface import DataProvider
from crypto_research.data.metadata import DatasetMetadata
from crypto_research.data.quality import DataQualityReporter
from crypto_research.data.store import ParquetDataStore
from crypto_research.data.validators import (
    DatasetValidationSummary,
    ValidationResult,
    ValidationStatus,
    run_validation_pipeline,
)

__all__ = [
    # HTTP client
    "BinanceFuturesClient",
    # Protocol
    "DataProvider",
    # Provider (reads from disk)
    "BinanceDataProvider",
    # Ingestion
    "DataIngestionPipeline",
    "IngestionResult",
    "PipelineResult",
    # Storage
    "ParquetDataStore",
    # Catalog
    "DataCatalog",
    "DatasetInfo",
    # Metadata
    "DatasetMetadata",
    # Quality
    "DataQualityReporter",
    # Validators
    "DatasetValidationSummary",
    "ValidationResult",
    "ValidationStatus",
    "run_validation_pipeline",
]
