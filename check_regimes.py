import pandas as pd
from datetime import datetime, timezone
from crypto_research.config.loader import load_config, find_project_root
from crypto_research.data.catalog import DataCatalog
from crypto_research.research.regimes.classifier import RegimeClassifier, TrendRegime

project_root = find_project_root()
config = load_config(project_root / "config" / "config.yaml")
catalog = DataCatalog(
    processed_dir=config.data.processed_dir,
    raw_dir=config.data.raw_dir,
    metadata_dir=config.data.metadata_dir,
    market_type=config.data.market_type,
)

tf = "1h"
ASSETS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
classifier = RegimeClassifier(config.robustness.regime)
btc_df = catalog.load("BTCUSDT", tf)
btc_df = classifier.classify_dataframe(btc_df)

all_trends = pd.DataFrame(index=btc_df.index)
for asset in ASSETS:
    df = catalog.load(asset, tf)
    if df.empty: continue
    df = classifier.classify_dataframe(df)
    all_trends[asset] = df['trend_regime'] == TrendRegime.TREND_UP.value

breadth_pct = all_trends.mean(axis=1)

longs = 0
shorts = 0
ranges = 0
for ts, row in btc_df.iterrows():
    btc_trend = row['trend_regime']
    breadth = breadth_pct.loc[ts] if ts in breadth_pct.index else 0.5
    if btc_trend == TrendRegime.TREND_UP.value and breadth >= 0.50:
        longs += 1
    elif btc_trend == TrendRegime.TREND_DOWN.value and breadth < 0.50:
        shorts += 1
    else:
        ranges += 1

print(f"Long Regimes: {longs}, Short Regimes: {shorts}, Range/Conflict: {ranges}")
