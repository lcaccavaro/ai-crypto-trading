import pandas as pd
from crypto_research.config.loader import load_config, find_project_root
from crypto_research.data.catalog import DataCatalog
project_root = find_project_root()
config = load_config(project_root / "config" / "config.yaml")
catalog = DataCatalog(processed_dir=config.data.processed_dir, raw_dir=config.data.raw_dir, metadata_dir=config.data.metadata_dir, market_type=config.data.market_type)
df = catalog.load("BTCUSDT", "1h")
print("Index:", df.index.name, type(df.index))
print("Columns:", df.columns)
