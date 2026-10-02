"""
╔══════════════════════════════════════════════════════════════╗
║              RODAR BACKTEST — PONTO DE ENTRADA               ║
╚══════════════════════════════════════════════════════════════╝
Como usar:
    cd /Users/lucascaccavaro/Documents/dev/ai-crypto-trading
    source .venv/bin/activate
    python rodar_backtest.py

Troque STRATEGY_ID por qualquer um dos 26 IDs de estratégia.
Estratégias disponíveis:
  Trend:         EMA_CROSS_001, TRIPLE_EMA_001, PRICE_VS_EMA_001, EMA_SLOPE_001
  Momentum:      RSI_MOMENTUM_001, ROC_MOMENTUM_001, MACD_MOMENTUM_001, MULTI_MOM_001
  Mean Rev:      BB_REVERSION_001, RSI_EXTREME_001, ZSCORE_REV_001, EMA_DISTANCE_001
  Breakout:      DONCHIAN_001, RANGE_BREAK_001, VOL_BREAK_001, ATR_CHANNEL_001
  Volatility:    ATR_EXPAND_001, VOL_COMPRESS_001, BB_WIDTH_001
  Volume:        VOL_SPIKE_001, VOL_WGT_MOM_001, VOL_BREAK_CONF_001
  Multi:         TREND_MOM_VOL_001, TREND_VOL_MOM_001
  Mkt Structure: HH_HL_001, VOL_REGIME_001
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from crypto_research.config.loader import load_config
from crypto_research.data.catalog import DataCatalog
from crypto_research.backtest.engine import BacktestEngine
from crypto_research.backtest.result import BacktestResultWriter
from crypto_research.backtest.strategy_adapter import StrategyAdapter

import crypto_research.strategies  # registra todas as 26 estratégias no REGISTRY
from crypto_research.strategies.registry import REGISTRY


# ─── EDITE AQUI ──────────────────────────────────────────────
STRATEGY_ID      = "RSI_MOMENTUM_001"  # ID da estratégia (veja lista acima)
RUN_ID           = "MANUAL_RUN_001"    # identificador desta execução
SALVAR_RESULTADO = True                 # salva arquivos CSV/JSON em results/?
# ─────────────────────────────────────────────────────────────


def main():
    print("=" * 62)
    print("  CRYPTO RESEARCH LAB — Backtest Runner")
    print("=" * 62)

    # 1. Configuração
    print("\n📋 Carregando configuração...")
    config = load_config(Path("config/config.yaml"))
    print(f"   Símbolo:     {config.backtest.symbols}")
    print(f"   Timeframe:   {config.backtest.timeframes}")
    print(f"   Período:     {config.backtest.start_date} → {config.backtest.end_date}")
    print(f"   Capital:     ${config.capital.initial_balance:,.2f}")
    print(f"   Risco/trade: {config.risk.risk_per_trade_pct}%")
    print(f"   R/R:         {config.risk.risk_reward_ratio}")

    # 2. Dados
    print("\n📦 Verificando dados disponíveis...")
    catalog = DataCatalog(
        processed_dir=config.data.processed_dir,
        raw_dir=config.data.raw_dir,
        metadata_dir=config.data.metadata_dir,
        market_type=config.data.market_type,
    )
    datasets = catalog.list_datasets()
    if not datasets:
        print("❌ ERRO: Nenhum dado processado encontrado!")
        print("   Execute primeiro a ingestão de dados.")
        return
    for ds in datasets:
        start = ds.actual_start or "?"
        end   = ds.actual_end   or "?"
        print(f"   ✅ {ds.symbol} {ds.timeframe} — {ds.row_count:,} candles ({start} → {end})")

    # 3. Estratégia
    print(f"\n🎯 Estratégia: {STRATEGY_ID}")
    if STRATEGY_ID not in REGISTRY:
        print(f"❌ Estratégia '{STRATEGY_ID}' não encontrada!")
        print(f"   Disponíveis: {REGISTRY.strategy_ids()}")
        return

    base_strategy = REGISTRY.instantiate(STRATEGY_ID)
    strategy = StrategyAdapter(
        strategy=base_strategy,
        rr_ratio=config.risk.risk_reward_ratio,
        stop_atr_mult=1.5,
    )
    info = REGISTRY.get(STRATEGY_ID)._info
    print(f"   Nome:       {info.name}")
    print(f"   Categoria:  {info.category}")
    print(f"   Parâmetros: {base_strategy.parameters}")

    # 4. Executa
    print(f"\n🚀 Iniciando simulação (pode levar 15-30 segundos)...")
    engine = BacktestEngine(catalog=catalog, config=config)
    result = engine.run(strategy=strategy, run_id=RUN_ID)

    # 5. Resultados
    print("\n" + "=" * 62)
    print("  RESULTADOS DO BACKTEST")
    print("=" * 62)

    m = result.metrics
    win_pct = m.win_rate * 100
    pf_str  = f"{m.profit_factor:.2f}" if m.profit_factor is not None else "N/A"

    print(f"\n📊 PERFORMANCE:")
    print(f"   Capital inicial:   ${m.initial_balance:>12,.2f}")
    print(f"   Capital final:     ${m.final_equity:>12,.2f}")
    print(f"   Retorno total:     {m.total_return_pct:>+10.2f}%")
    print(f"   Drawdown máximo:   {m.max_drawdown_pct:>10.2f}%")

    print(f"\n📈 TRADES:")
    print(f"   Total de trades:   {m.total_trades:>10}")
    print(f"   Vencedores:        {m.winning_trades:>10}")
    print(f"   Perdedores:        {m.losing_trades:>10}")
    print(f"   Win rate:          {win_pct:>10.1f}%")
    print(f"   Profit factor:     {pf_str:>10}")
    print(f"   Net P&L:           ${m.net_pnl:>+11.2f}")

    if m.average_R is not None:
        print(f"   R médio/trade:     {m.average_R:>+10.2f}R")

    trades = sorted(result.trades, key=lambda t: t.net_pnl, reverse=True)
    if trades:
        print(f"\n🏆 MELHORES 5 TRADES:")
        print(f"   {'Entrada':<19} {'Símbolo':<10} {'P&L $':>10} {'R':>6}")
        print(f"   {'-'*19} {'-'*10} {'-'*10} {'-'*6}")
        for t in trades[:5]:
            entry_ts = t.entry_fill.timestamp.strftime("%Y-%m-%d %H:%M") if t.entry_fill else "-"
            r_str    = f"{t.r_multiple:+.1f}R" if t.r_multiple is not None else "—"
            print(f"   {entry_ts:<19} {t.asset:<10} ${t.net_pnl:>+9.2f} {r_str:>6}")

        print(f"\n💀 PIORES 5 TRADES:")
        print(f"   {'Entrada':<19} {'Símbolo':<10} {'P&L $':>10} {'R':>6}")
        print(f"   {'-'*19} {'-'*10} {'-'*10} {'-'*6}")
        for t in trades[-5:][::-1]:
            entry_ts = t.entry_fill.timestamp.strftime("%Y-%m-%d %H:%M") if t.entry_fill else "-"
            r_str    = f"{t.r_multiple:+.1f}R" if t.r_multiple is not None else "—"
            print(f"   {entry_ts:<19} {t.asset:<10} ${t.net_pnl:>+9.2f} {r_str:>6}")

    else:
        print("\n⚠️  Nenhum trade executado neste período.")
        print("   Dicas:")
        print("   1. Esta estratégia pode ser 'evento-based' e só dispara em cruzamentos raros")
        print("   2. Tente estratégias com mais sinais: RSI_MOMENTUM_001, BB_REVERSION_001")
        print("   3. Verifique orders.csv para ver ordens rejeitadas pelo RiskGate")

    # Ordens rejeitadas
    rejected = [o for o in result.orders if hasattr(o, 'status') and str(o.status) in ('REJECTED', 'OrderStatus.REJECTED')]
    if rejected:
        print(f"\n🚫 Ordens rejeitadas pelo RiskGate: {len(rejected)}")
        from collections import Counter
        reasons = Counter(str(getattr(o, 'rejection_reason', 'unknown')) for o in rejected)
        for reason, count in reasons.most_common():
            print(f"   {reason}: {count}x")

    # 6. Salva
    if SALVAR_RESULTADO and result.trades:
        out_dir = Path(f"results/backtests/{RUN_ID}")
        writer  = BacktestResultWriter(result=result, run_dir=out_dir)
        writer.write_all()
        print(f"\n💾 Resultados salvos em: {out_dir}/")
        print(f"   trades.csv, equity_curve.csv, metrics.json, orders.csv")

    print("\n✅ Concluído!")
    print("=" * 62)


if __name__ == "__main__":
    main()

    print("\n✅ Concluído!")
    print("=" * 62)


if __name__ == "__main__":
    main()
