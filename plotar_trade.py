import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from datetime import timedelta

def load_candles(asset: str, start_time, end_time, raw_dir="data/processed"):
    parquet_path = Path(raw_dir) / "binance" / "futures" / asset / "15m" / f"{asset}_15m.parquet"
    if not parquet_path.exists():
        print(f"   ⚠️ Dados não encontrados em {parquet_path}")
        return None
    
    df = pd.read_parquet(parquet_path)
    if 'timestamp' in df.columns:
        df = df.set_index('timestamp')
    df.index = pd.to_datetime(df.index)
    
    window_start = start_time - timedelta(days=1)
    window_end = end_time + timedelta(days=1)
    
    if df.index.tz is None and window_start.tz is not None:
        window_start = window_start.tz_localize(None)
        window_end = window_end.tz_localize(None)
    elif df.index.tz is not None and window_start.tz is None:
        window_start = window_start.tz_localize(df.index.tz)
        window_end = window_end.tz_localize(df.index.tz)
    
    mask = (df.index >= window_start) & (df.index <= window_end)
    filtered_df = df[mask].copy()
    
    # Converter para fuso horário de Brasília/SP para bater com o TradingView do usuário
    if filtered_df.index.tz is not None:
        filtered_df.index = filtered_df.index.tz_convert('America/Sao_Paulo')
    else:
        filtered_df.index = filtered_df.index.tz_localize('UTC').tz_convert('America/Sao_Paulo')
        
    return filtered_df

def plot_trade(trade, stop_price, target_price, candles, out_file: Path):
    fig = go.Figure()

    # Cores Premium exatas do MarketHunter
    BG_COLOR = "#0B101E"
    GRID_COLOR = "#1A202C"
    TEXT_COLOR = "#9CA3AF"
    
    COLOR_ENTRY = "#00BCD4"
    COLOR_TARGET = "#B39DDB"
    COLOR_STOP = "#FF9800"
    
    COLOR_BULL = "#26A69A"
    COLOR_BEAR = "#EF5350"

    # Candlestick principal
    fig.add_trace(go.Candlestick(
        x=candles.index,
        open=candles['open'],
        high=candles['high'],
        low=candles['low'],
        close=candles['close'],
        name='Preço',
        increasing_line_color=COLOR_BULL, increasing_fillcolor=COLOR_BULL,
        decreasing_line_color=COLOR_BEAR, decreasing_fillcolor=COLOR_BEAR,
        showlegend=False
    ))

    entry_price = trade['entry_price']
    
    # Helper para adicionar linhas horizontais com label estilizado na esquerda
    def add_level_line(y_val, color, text):
        if pd.notna(y_val):
            fig.add_hline(
                y=y_val, 
                line_dash="dash", 
                line_color=color, 
                line_width=1.5,
                opacity=0.8,
                annotation=dict(
                    text=f"<b>{text} ${y_val:,.4f}</b>",
                    font=dict(color=BG_COLOR if color in [COLOR_ENTRY, COLOR_TARGET] else "white", size=14, family="Inter, Arial, sans-serif"),
                    bgcolor=color,
                    borderpad=8,
                    bordercolor=color,
                    borderwidth=1
                ),
                annotation_position="left"
            )

    add_level_line(target_price, COLOR_TARGET, "Stop Gain")
    add_level_line(entry_price, COLOR_ENTRY, "Entry")
    add_level_line(stop_price, COLOR_STOP, "Stop")

    # Marcador de Entrada (Triângulo com texto ENTRY)
    # Colocar um pouquinho abaixo da mínima do candle
    entry_candle_time = trade['entry_time']
    y_marker = candles.loc[entry_candle_time, 'low'] * 0.998 if entry_candle_time in candles.index else entry_price * 0.998
    
    fig.add_trace(go.Scatter(
        x=[entry_candle_time],
        y=[y_marker],
        mode='markers+text',
        marker=dict(symbol='triangle-up', size=24, color=COLOR_ENTRY),
        text=["<b>ENTRY</b>"],
        textposition="bottom center",
        textfont=dict(color=COLOR_ENTRY, size=13, family="Inter, Arial, sans-serif"),
        showlegend=False
    ))
    
    # Marcador de Saída (Estrela)
    fig.add_trace(go.Scatter(
        x=[trade['exit_time']],
        y=[trade['exit_price']],
        mode='markers',
        marker=dict(symbol='star', size=18, color='#FFD700', line=dict(width=1, color='black')),
        name=f"Saída ({trade['exit_reason']})",
        showlegend=False
    ))

    # Título Customizado (Top Left)
    title_html = f"<b style='font-size:32px; color:white; font-family:Inter, Arial, sans-serif;'>{trade['asset']}</b> <span style='font-size:18px; color:{COLOR_BULL}; font-weight:bold; font-family:Inter, Arial, sans-serif;'>LONG</span><br><span style='font-size:15px; color:#9CA3AF; font-family:Inter, Arial, sans-serif;'>Timeframe: 15m</span>"
    
    fig.add_annotation(
        text=title_html,
        xref="paper", yref="paper",
        x=0.0, y=1.12,
        showarrow=False,
        xanchor="left", yanchor="bottom",
        align="left"
    )
    
    # Badge CONFIRMED (Top Right)
    pnl = trade['net_pnl']
    badge_color = COLOR_ENTRY if pnl > 0 else COLOR_BEAR
    badge_text = "CONFIRMED" if pnl > 0 else "STOPPED"
    fig.add_annotation(
        text=f"<b>{badge_text}</b>",
        xref="paper", yref="paper",
        x=1.0, y=1.12,
        showarrow=False,
        xanchor="right", yanchor="bottom",
        font=dict(color=BG_COLOR if pnl > 0 else "white", size=16, family="Inter, Arial, sans-serif"),
        bgcolor=badge_color,
        borderpad=10,
        bordercolor=badge_color,
        borderwidth=1,
    )

    # Assinatura (Bottom Left)
    fig.add_annotation(
        text="MarketHunter.ai - MH1",
        xref="paper", yref="paper",
        x=0.0, y=-0.08,
        showarrow=False,
        xanchor="left", yanchor="top",
        font=dict(color="#6B7280", size=13, family="Inter, Arial, sans-serif")
    )

    # Layout Global: Tamanho fixo e proporções exatas da imagem
    fig.update_layout(
        width=1200,
        height=675,
        template="plotly_dark",
        plot_bgcolor=BG_COLOR,
        paper_bgcolor=BG_COLOR,
        margin=dict(l=180, r=100, t=130, b=80),
        xaxis=dict(
            showgrid=True, gridcolor=GRID_COLOR, 
            zeroline=False, showline=False,
            rangeslider=dict(visible=False),
            tickfont=dict(color=TEXT_COLOR, size=12)
        ),
        yaxis=dict(
            side="right", 
            showgrid=True, gridcolor=GRID_COLOR, 
            zeroline=False, showline=False,
            tickfont=dict(color=TEXT_COLOR, size=13),
            tickformat=".4f",
            ticklabelposition="outside right"
        )
    )

    fig.write_html(str(out_file))

def generate_all_trade_charts(run_dir: str):
    trades_path = Path(run_dir) / "trades.csv"
    orders_path = Path(run_dir) / "orders.csv"
    
    if not trades_path.exists() or not orders_path.exists():
        return
        
    trades = pd.read_csv(trades_path)
    if trades.empty:
        return
        
    trades['entry_time'] = pd.to_datetime(trades['entry_time'], format='ISO8601')
    trades['exit_time'] = pd.to_datetime(trades['exit_time'], format='ISO8601')
    
    orders = pd.read_csv(orders_path)
    orders['timestamp'] = pd.to_datetime(orders['timestamp'], format='ISO8601')
    
    charts_dir = Path(run_dir) / "charts"
    charts_dir.mkdir(exist_ok=True)
    
    print(f"\n📊 Gerando {len(trades)} gráficos de trades interativos...")
    
    for i, trade in trades.iterrows():
        mask = (orders['asset'] == trade['asset']) & (orders['status'] == 'active') & (orders['timestamp'] <= trade['entry_time'])
        valid_orders = orders[mask].sort_values(by="timestamp", ascending=False)
        
        stop_price = None
        target_price = None
        if not valid_orders.empty:
            entry_order = valid_orders.iloc[0]
            stop_price = entry_order['stop_price']
            target_price = entry_order['target_price']
            
        candles = load_candles(trade['asset'], trade['entry_time'], trade['exit_time'])
        if candles is not None and not candles.empty:
            
            # Converter os tempos do trade para bater com o fuso do gráfico (SP)
            if trade['entry_time'].tz is not None:
                trade_entry_local = trade['entry_time'].tz_convert('America/Sao_Paulo')
                trade_exit_local = trade['exit_time'].tz_convert('America/Sao_Paulo')
            else:
                trade_entry_local = trade['entry_time'].tz_localize('UTC').tz_convert('America/Sao_Paulo')
                trade_exit_local = trade['exit_time'].tz_localize('UTC').tz_convert('America/Sao_Paulo')
                
            trade_copy = trade.copy()
            trade_copy['entry_time'] = trade_entry_local
            trade_copy['exit_time'] = trade_exit_local
            
            safe_time = trade_copy['entry_time'].strftime("%Y%m%d_%H%M")
            pnl_str = "WIN" if trade_copy['net_pnl'] > 0 else "LOSS"
            out_file = charts_dir / f"trade_{i+1}_{trade_copy['asset']}_{safe_time}_{pnl_str}.html"
            plot_trade(trade_copy, stop_price, target_price, candles, out_file)
        else:
            print(f"   ⚠️ Sem candles para o trade {i+1} de {trade['asset']}")
            
    print(f"   ✅ Gráficos salvos em: {charts_dir}/")
