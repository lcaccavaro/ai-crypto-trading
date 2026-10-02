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

class MultiStrategyAdapter:
    """
    Roda todas as estratégias disponíveis simultaneamente no engine.
    Retorna o sinal com a maior "strength" em caso de conflitos.
    """
    def __init__(self, rr_ratio: float, stop_pct: float = 3.0):
        self._adapters = []
        for strat_id in REGISTRY.strategy_ids():
            base_strategy = REGISTRY.instantiate(strat_id)
            adapter = StrategyAdapter(base_strategy, rr_ratio=rr_ratio, stop_pct=stop_pct)
            self._adapters.append(adapter)
            
    @property
    def name(self) -> str:
        return "MASSIVE_MULTI_STRATEGY"
        
    @property
    def version(self) -> str:
        return "1.0.0"
        
    def on_candle(self, close_price: float, symbol: str, timeframe: str, timestamp: datetime) -> dict | None:
        best_signal = None
        
        for adapter in self._adapters:
            signal = adapter.on_candle(close_price, symbol, timeframe, timestamp)
            if signal is not None:
                if best_signal is None or signal["strength"] > best_signal["strength"]:
                    best_signal = signal
                    
        return best_signal

    def reset(self) -> None:
        for adapter in self._adapters:
            adapter.reset()

def run_backtest_worker(task):
    task_id, rr, tf, max_trades, assets = task
    
    project_root = find_project_root()
    base_config_path = project_root / "config" / "config.yaml"
    config = load_config(base_config_path)
    
    # Aplicar overrides da task
    config.backtest.symbols = assets
    config.backtest.timeframes = [tf]
    config.risk.risk_reward_ratio = rr
    config.risk.max_concurrent_positions = max_trades  # Passamos um valor alto (ex: 1000) para "sem limite"
    config.capital.initial_balance = 500.0
    config.risk.max_total_exposure_pct = 9999.0
    config.risk.max_asset_exposure_pct = 9999.0
    
    # Remover stop win / stop loss diário (usando valores muito altos para simular)
    config.risk.daily_profit_target_pct = 999.0
    config.risk.daily_loss_limit_pct = 999.0
    
    # Histórico de apenas 1 Mês (30 dias)
    end_date = datetime.now()
    start_date = end_date - pd.Timedelta(days=30)
    config.backtest.start_date = start_date.strftime("%Y-%m-%d")
    config.backtest.end_date = end_date.strftime("%Y-%m-%d")
    
    # Desabilita logs excessivos para não flodar o console em modo multiprocessing
    config.logging.level = "WARNING"
    
    catalog = DataCatalog(
        processed_dir=config.data.processed_dir,
        raw_dir=config.data.raw_dir,
        metadata_dir=config.data.metadata_dir,
        market_type=config.data.market_type,
    )
    
    multi_strategy = MultiStrategyAdapter(rr_ratio=rr)
    engine = BacktestEngine(catalog=catalog, config=config)
    
    run_name = f"MINI_TEST_RR{rr}_TF{tf}_1MONTH"
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando {run_name}...")
    
    try:
        start_time = time.time()
        result = engine.run(strategy=multi_strategy, run_id=run_name)
        elapsed = time.time() - start_time
        
        m = result.metrics
        
        # Salva o resultado no formato padrao do sistema tambem para podermos olhar os graficos
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
    print(" MINI BACKTEST RUNNER (1 SCENARIO)")
    print("="*60)
    
    # TODAS AS 28 MOEDAS DISPONÍVEIS E COM DADOS NO ÚLTIMO MÊS
    ASSETS = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", 
        "ADAUSDT", "DOGEUSDT", "TRXUSDT", "DOTUSDT", 
        "LTCUSDT", "BCHUSDT", "LINKUSDT", "AVAXUSDT", 
        "XLMUSDT", "ATOMUSDT", "UNIUSDT", "XMRUSDT", "ETCUSDT", 
        "FILUSDT", "ICPUSDT", "VETUSDT", "NEARUSDT", "ALGOUSDT", 
        "QNTUSDT", "APEUSDT", "SANDUSDT", "MANAUSDT", "AXSUSDT"
    ]
    
    # APENAS RR 2.0, TF 1h, sem limite de trades
    RRS = [2.0]
    TFS = ["1h"]
    MAX_TRADES = [1000] # Representa "sem limite" prático
    
    tasks = []
    task_id = 0
    for rr in RRS:
        for tf in TFS:
            for max_t in MAX_TRADES:
                tasks.append((task_id, rr, tf, max_t, ASSETS))
                task_id += 1
                
    print(f"Total de backtests a executar: {len(tasks)}")
    
    results = []
    # Executa sem multiprocessing por ser apenas 1 task (facilita ver erros e logs no console)
    for task in tasks:
        res = run_backtest_worker(task)
        results.append(res)
            
    print("\n" + "="*60)
    print(" GERANDO BASE DE CONHECIMENTO (MINI TESTE)")
    print("="*60)
    
    successful = [r for r in results if r["status"] == "SUCCESS"]
    
    if not successful:
        print("❌ Todos os testes falharam.")
        sys.exit(1)
        
    df = pd.DataFrame(successful)
    df = df.sort_values(by="final_equity", ascending=False)
    
    # 1. Salvar CSV
    project_root = find_project_root()
    kb_csv = project_root / "results" / "MINI_KNOWLEDGE_BASE.csv"
    kb_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(kb_csv, index=False)
    print(f"✅ CSV gravado em: {kb_csv}")
    
    # 2. Gerar Markdown Report
    kb_md = project_root / "results" / "MINI_KNOWLEDGE_BASE_REPORT.md"
    
    with open(kb_md, "w", encoding="utf-8") as f:
        f.write("# Relatório da Base de Conhecimento - Mini Teste (BTCUSDT, 1h, 1 Mês)\n\n")
        f.write(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Resultado\n\n")
        for i, row in df.iterrows():
            f.write(f"### {row['run_name']}\n")
            f.write(f"- **Ativo:** BTCUSDT\n")
            f.write(f"- **Risco/Retorno:** {row['rr_ratio']}\n")
            f.write(f"- **Tempo Gráfico:** {row['timeframe']}\n")
            f.write(f"- **Período Histórico:** Últimos 30 dias\n")
            f.write(f"- **Lucro Líquido:** ${row['net_pnl']:.2f}\n")
            f.write(f"- **Capital Final:** ${row['final_equity']:.2f}\n")
            f.write(f"- **Retorno Total:** {row['total_return_pct']:.2f}%\n")
            f.write(f"- **Max Drawdown:** {row['max_drawdown_pct']:.2f}%\n")
            f.write(f"- **Win Rate:** {row['win_rate']:.2f}%\n")
            f.write(f"- **Total de Trades:** {row['total_trades']}\n")
            f.write(f"- **Profit Factor:** {row['profit_factor']:.2f}\n")
            f.write(f"- **Tempo de Processamento:** {row['elapsed_seconds']:.1f} segundos\n")
            f.write("\n---\n\n")
            
    print(f"✅ Relatório Markdown gravado em: {kb_md}")
    print("\nProcesso concluído com sucesso!")

if __name__ == "__main__":
    main()
