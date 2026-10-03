import sys
import copy
import time
import multiprocessing
from pathlib import Path
from datetime import datetime
from collections import deque

import pandas as pd

from crypto_research.config.loader import load_config, find_project_root
from crypto_research.data.catalog import DataCatalog
from crypto_research.backtest.engine import BacktestEngine
from crypto_research.backtest.strategy_adapter import StrategyAdapter
from crypto_research.strategies.registry import REGISTRY
import crypto_research.strategies  # Registra todas as estratégias
from crypto_research.core.domain import SignalDirection
from crypto_research.research.regimes.classifier import RegimeClassifier, TrendRegime

def precompute_market_regimes(config, catalog: DataCatalog, assets: list[str], tf: str) -> dict:
    """
    Pré-calcula a tendência do BTC e a porcentagem de moedas em alta (Market Breadth)
    para cada timestamp do histórico, usando o RegimeClassifier (livre de Lookahead bias).
    """
    print("📈 Calculando Market Regimes globais (BTC Trend + Market Breadth)...")
    classifier = RegimeClassifier(config.robustness.regime)
    global_regimes = {}
    
    btc_df = catalog.load("BTCUSDT", tf)
    if btc_df.empty:
        print("⚠️ Dados de BTCUSDT não encontrados. Abortando cálculo de regime.")
        return {}
    
    btc_df = classifier.classify_dataframe(btc_df)
    
    # Calcula a tendência de todos os ativos para o Breadth
    all_trends = pd.DataFrame(index=btc_df.index)
    for asset in assets:
        df = catalog.load(asset, tf)
        if df.empty:
            continue
        df = classifier.classify_dataframe(df)
        all_trends[asset] = df['trend_regime'] == TrendRegime.TREND_UP.value
        
    breadth_pct = all_trends.mean(axis=1)
    
    for idx, row in btc_df.iterrows():
        ts_val = row['timestamp']
        global_regimes[pd.Timestamp(ts_val)] = {
            "btc_trend": row['trend_regime'],
            "breadth_up_pct": breadth_pct.loc[idx] if idx in breadth_pct.index else 0.5
        }
        
    print(f"✅ Regimes globais calculados para {len(global_regimes)} candles.")
    return global_regimes


class MultiStrategyAdapter:
    """
    Roda todas as estratégias disponíveis simultaneamente no engine.
    Filtra as operações via Market Regime Gate (BTC Trend & Breadth).
    Inverte matematicamente os sinais LONG originais para SHORT quando em mercado de baixa.
    """
    def __init__(self, rr_ratio: float, global_regimes: dict, stop_pct: float = 3.0):
        self._adapters = []
        self.global_regimes = global_regimes
        for strat_id in REGISTRY.strategy_ids():
            base_strategy = REGISTRY.instantiate(strat_id)
            adapter = StrategyAdapter(base_strategy, rr_ratio=rr_ratio, stop_pct=stop_pct)
            self._adapters.append(adapter)
            
    @property
    def name(self) -> str:
        return "MASSIVE_MULTI_STRATEGY_WITH_GATE"
        
    @property
    def version(self) -> str:
        return "2.0.0"
        
    def on_candle(self, close_price: float, symbol: str, timeframe: str, timestamp: datetime) -> dict | None:
        # Pega a "foto" do mercado global no exato candle atual
        regime = self.global_regimes.get(pd.Timestamp(timestamp))
        if not regime:
            return None
            
        btc_trend = regime["btc_trend"]
        breadth = regime["breadth_up_pct"]
        
        # MARKET REGIME GATE
        # Somente autoriza LONG se BTC está UP e maioria do mercado (>50%) está UP
        if btc_trend == TrendRegime.TREND_UP.value and breadth >= 0.50:
            allowed_direction = SignalDirection.LONG
        # Somente autoriza SHORT se BTC está DOWN e maioria do mercado (<50%) está DOWN
        elif btc_trend == TrendRegime.TREND_DOWN.value and breadth < 0.50:
            allowed_direction = SignalDirection.SHORT
        else:
            # Em RANGE ou divergências (BTC sobe mas altcoins caem), NÃO OPERAR.
            return None
            
        best_signal = None
        
        for adapter in self._adapters:
            signal = adapter.on_candle(close_price, symbol, timeframe, timestamp)
            if signal is not None:
                if best_signal is None or signal["strength"] > best_signal["strength"]:
                    best_signal = signal
                    
        if best_signal is not None:
            # Se o gate decidiu por SHORT, invertemos mecanicamente a estratégia LONG.
            if allowed_direction == SignalDirection.SHORT:
                new_stop = None
                new_target = None
                
                # Invertendo o Stop e Target usando o preço atual como eixo de rotação
                if best_signal.get("stop_price"):
                    new_stop = close_price + (close_price - best_signal["stop_price"])
                if best_signal.get("target_price"):
                    new_target = close_price - (best_signal["target_price"] - close_price)
                
                best_signal["direction"] = SignalDirection.SHORT
                best_signal["stop_price"] = new_stop
                best_signal["target_price"] = new_target
            else:
                best_signal["direction"] = SignalDirection.LONG
                
            return best_signal
            
        return None

    def reset(self) -> None:
        for adapter in self._adapters:
            adapter.reset()

def run_backtest_worker(task):
    task_id, rr, tf, max_trades, assets, global_regimes = task
    
    project_root = find_project_root()
    base_config_path = project_root / "config" / "config.yaml"
    config = load_config(base_config_path)
    
    # Aplicar overrides da task
    config.backtest.symbols = assets
    config.backtest.timeframes = [tf]
    config.risk.risk_reward_ratio = rr
    config.risk.max_concurrent_positions = max_trades
    config.capital.initial_balance = 500.0
    config.risk.max_total_exposure_pct = 9999.0
    config.risk.max_asset_exposure_pct = 9999.0
    
    config.risk.daily_profit_target_pct = 999.0
    config.risk.daily_loss_limit_pct = 999.0
    
    end_date = datetime.now()
    start_date = end_date - pd.Timedelta(days=30)
    config.backtest.start_date = start_date.strftime("%Y-%m-%d")
    config.backtest.end_date = end_date.strftime("%Y-%m-%d")
    
    config.logging.level = "WARNING"
    
    catalog = DataCatalog(
        processed_dir=config.data.processed_dir,
        raw_dir=config.data.raw_dir,
        metadata_dir=config.data.metadata_dir,
        market_type=config.data.market_type,
    )
    
    multi_strategy = MultiStrategyAdapter(rr_ratio=rr, global_regimes=global_regimes)
    engine = BacktestEngine(catalog=catalog, config=config)
    
    run_name = f"MINI_TEST_RR{rr}_TF{tf}_1MONTH_WITH_GATE"
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando {run_name}...")
    
    try:
        start_time = time.time()
        result = engine.run(strategy=multi_strategy, run_id=run_name)
        elapsed = time.time() - start_time
        
        m = result.metrics
        
        from crypto_research.backtest.result import BacktestResultWriter
        out_dir = Path(f"results/backtests/{run_name}")
        writer  = BacktestResultWriter(base_dir="results/backtests")
        writer.write(result)
        
        return {
            "run_name": run_name,
            "rr_ratio": rr,
            "timeframe": tf,
            "max_trades": max_trades,
            "initial_balance": m.initial_balance,
            "final_equity": m.final_equity,
            "total_return_pct": m.total_return_pct,
            "max_drawdown_pct": m.max_drawdown_pct,
            "total_trades": m.total_trades,
            "win_rate": m.win_rate * 100,
            "profit_factor": m.profit_factor if m.profit_factor else 0.0,
            "net_pnl": m.net_pnl,
            "elapsed_seconds": elapsed,
            "status": "SUCCESS",
            "error": None
        }
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ERRO em {run_name}: {e}")
        return {
            "run_name": run_name,
            "rr_ratio": rr,
            "timeframe": tf,
            "max_trades": max_trades,
            "status": "FAILED",
            "error": str(e)
        }

def main():
    print("="*60)
    print(" MINI BACKTEST RUNNER WITH MARKET REGIME GATE")
    print("="*60)
    
    project_root = find_project_root()
    base_config_path = project_root / "config" / "config.yaml"
    config = load_config(base_config_path)
    
    ASSETS = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", 
        "ADAUSDT", "DOGEUSDT", "TRXUSDT", "DOTUSDT", 
        "LTCUSDT", "BCHUSDT", "LINKUSDT", "AVAXUSDT", 
        "XLMUSDT", "ATOMUSDT", "UNIUSDT", "XMRUSDT", "ETCUSDT", 
        "FILUSDT", "ICPUSDT", "VETUSDT", "NEARUSDT", "ALGOUSDT", 
        "QNTUSDT", "APEUSDT", "SANDUSDT", "MANAUSDT", "AXSUSDT"
    ]
    
    RRS = [2.0]
    TFS = ["1h"]
    MAX_TRADES = [1000]
    
    catalog = DataCatalog(
        processed_dir=config.data.processed_dir,
        raw_dir=config.data.raw_dir,
        metadata_dir=config.data.metadata_dir,
        market_type=config.data.market_type,
    )
    
    # 1. Pré-computa o regime global de mercado ANTES de iniciar os backtests
    tf_for_regime = TFS[0]
    global_regimes = precompute_market_regimes(config, catalog, ASSETS, tf_for_regime)
    
    tasks = []
    task_id = 0
    for rr in RRS:
        for tf in TFS:
            for max_t in MAX_TRADES:
                tasks.append((task_id, rr, tf, max_t, ASSETS, global_regimes))
                task_id += 1
                
    print(f"Total de backtests a executar: {len(tasks)}")
    
    results = []
    for task in tasks:
        res = run_backtest_worker(task)
        results.append(res)
            
    print("\n" + "="*60)
    print(" GERANDO BASE DE CONHECIMENTO")
    print("="*60)
    
    successful = [r for r in results if r["status"] == "SUCCESS"]
    
    if not successful:
        print("❌ Todos os testes falharam.")
        sys.exit(1)
        
    df = pd.DataFrame(successful)
    df = df.sort_values(by="final_equity", ascending=False)
    
    kb_csv = project_root / "results" / "MINI_KNOWLEDGE_BASE_GATED.csv"
    kb_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(kb_csv, index=False)
    print(f"✅ CSV gravado em: {kb_csv}")
    
    kb_md = project_root / "results" / "MINI_KNOWLEDGE_BASE_GATED_REPORT.md"
    
    with open(kb_md, "w", encoding="utf-8") as f:
        f.write("# Relatório da Base de Conhecimento - Com Regime Gate\n\n")
        f.write(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Resultado\n\n")
        for i, row in df.iterrows():
            f.write(f"### {row['run_name']}\n")
            f.write(f"- **Ativo:** Portfólio (28 ativos)\n")
            f.write(f"- **Risco/Retorno:** {row['rr_ratio']}\n")
            f.write(f"- **Tempo Gráfico:** {row['timeframe']}\n")
            f.write(f"- **Lucro Líquido:** ${row['net_pnl']:.2f}\n")
            f.write(f"- **Capital Final:** ${row['final_equity']:.2f}\n")
            f.write(f"- **Retorno Total:** {row['total_return_pct']:.2f}%\n")
            f.write(f"- **Max Drawdown:** {row['max_drawdown_pct']:.2f}%\n")
            f.write(f"- **Win Rate:** {row['win_rate']:.2f}%\n")
            f.write(f"- **Total de Trades:** {row['total_trades']}\n")
            f.write(f"- **Profit Factor:** {row['profit_factor']:.2f}\n")
            f.write("\n---\n\n")
            
    print(f"✅ Relatório Markdown gravado em: {kb_md}")
    print("\nProcesso concluído com sucesso!")

if __name__ == "__main__":
    main()
