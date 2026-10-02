import sys
from pathlib import Path
from datetime import datetime, timedelta

from crypto_research.config.loader import load_config, find_project_root
from crypto_research.data.ingestion import DataIngestionPipeline
from crypto_research.research.run_manager import RunManager
from crypto_research.utils.logging import setup_logging

ASSETS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", 
    "ADAUSDT", "DOGEUSDT", "TRXUSDT", "DOTUSDT", "MATICUSDT", 
    "LTCUSDT", "BCHUSDT", "LINKUSDT", "SHIBUSDT", "AVAXUSDT", 
    "XLMUSDT", "ATOMUSDT", "UNIUSDT", "XMRUSDT", "ETCUSDT", 
    "FILUSDT", "ICPUSDT", "VETUSDT", "NEARUSDT", "ALGOUSDT", 
    "QNTUSDT", "APEUSDT", "SANDUSDT", "MANAUSDT", "AXSUSDT"
]

TIMEFRAMES = ["5m", "15m", "1h", "4h"]

def main():
    project_root = find_project_root()
    config_path = project_root / "config" / "config.yaml"
    
    print("Loading base configuration...")
    config = load_config(config_path)

    # Modify config in memory for the massive ingestion
    config.assets = ASSETS
    config.timeframes = TIMEFRAMES
    
    # 5 years ago from today
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5 * 365)
    
    config.data.start_date = start_date.strftime("%Y-%m-%d")
    config.data.end_date = end_date.strftime("%Y-%m-%d")

    print(f"\n=======================================================")
    print(f"Starting MASSIVE data ingestion")
    print(f"Assets ({len(ASSETS)}): {', '.join(ASSETS[:5])}... etc")
    print(f"Timeframes ({len(TIMEFRAMES)}): {', '.join(TIMEFRAMES)}")
    print(f"Period: {config.data.start_date} to {config.data.end_date} (5 Years)")
    print(f"=======================================================\n")

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

    pipeline = DataIngestionPipeline(config=config, project_root=project_root)
    
    # Note: use_full_range=True forces it to use the 5-year config dates instead of DEMO_DAYS
    result = pipeline.run(
        use_full_range=True,
        run_id=research_run.run_id,
        run_dir=run_dir,
    )

    if result.failed:
        print(f"\n⚠️  {len(result.failed)} dataset(s) FAILED. See quality report.")
        sys.exit(1)
    else:
        print("\n✅ All historical data downloaded successfully.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDownload aborted by user.")
        sys.exit(0)
