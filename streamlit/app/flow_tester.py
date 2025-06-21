import os
import subprocess
import streamlit as st
import pandas as pd
import psycopg2
from psycopg2 import errors

# ─── Page config ─────────────────────────────────────────
st.set_page_config(
    page_title="Flow Tester: Portfolio → Backtest → Live Orders",
    layout="wide",
    initial_sidebar_state="expanded"
)

DSN            = os.getenv("DSN", "")
TRADEPLAN_DIR  = os.getenv("TRADEPLAN_DIR", "/app/liu_samples")
TLOG_LEVEL     = os.getenv("TLOG_LEVEL", "DEBUG")
REFRESH_MS     = int(os.getenv("REFRESH_INTERVAL_MS", 5000))
MAX_ROWS       = int(os.getenv("MAX_ROWS", 50))

# ─── Sidebar: 1) Initialize Portfolio ────────────────────
with st.sidebar:
    st.header("1) Initialize Portfolio")
    cash = st.number_input("Starting cash ($)", 1000, 1_000_000, 25_000, step=1000)
    if st.button("🔄 Initialize Portfolio"):
        res = subprocess.run(
            ["liu", "create", "portfolio", str(cash), f"--dsn={DSN}"],
            capture_output=True, text=True
        )
        if res.returncode == 0:
            st.success(f"Portfolio initialized to ${cash:,}")
        else:
            st.error(res.stderr)

    st.write("---")
    st.header("2) Run Backtest")
    symbols    = st.text_input("Symbols (CSV)", "AAPL,MSFT,NVDA")
    start_date = st.date_input("Start Date", value=pd.to_datetime("2025-01-01"))
    end_date   = st.date_input("End Date",   value=pd.to_datetime("today"))
    if st.button("▶️ Run Backtest"):
        with st.spinner("Running backtest... this can take a minute"):
            cmd = [
                "python3", "-m", "liualgotrader.enhanced_backtest",
                "--symbols",    symbols,
                "--start-date", start_date.strftime("%Y-%m-%d"),
                "--end-date",   end_date.strftime("%Y-%m-%d"),
                "--tradeplan",  f"{TRADEPLAN_DIR}/tradeplan.toml",
                "--diagnostics",f"{TRADEPLAN_DIR}/diagnostics.json",
                "--log-level",  TLOG_LEVEL
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            st.success("✅ Backtest complete!")
        else:
            st.error("❌ Backtest failed:\n" + proc.stderr)
        st.experimental_rerun()   # reload UI with new data

    st.write("---")
    st.header("3) Live Orders")
    st.write(f"Auto-refresh every {REFRESH_MS/1000:.1f}s")
    st_autorefresh = st.checkbox("Enable auto-refresh", value=True)

# ─── Recent Backtests ──────────────────────────────────────
st.title("📝 Recent Backtests")
@st.cache_data(ttl=REFRESH_MS//1000)
def load_backtests(n):
    q = """
      SELECT batch_id, run_at, symbols, win_rate, net_profit
        FROM backtests
       ORDER BY run_at DESC
       LIMIT %s
    """
    try:
        with psycopg2.connect(DSN) as conn:
            df = pd.read_sql(q, conn, params=(n,))
        df["run_at"] = pd.to_datetime(df["run_at"])
        return df
    except errors.UndefinedTable:
        return pd.DataFrame()

df_bt = load_backtests(MAX_ROWS)

# Metrics
col1, col2, col3 = st.columns(3)
if not df_bt.empty:
    last    = df_bt.iloc[0]
    avg_win = df_bt["win_rate"].mean() * 100
    col1.metric("Last Net Profit", f"${last.net_profit:.2f}")
    col2.metric("Last Win Rate", f"{last.win_rate*100:.1f}%")
    col3.metric("Avg Win Rate", f"{avg_win:.1f}%")
else:
    col1.metric("Last Net Profit", "–")
    col2.metric("Last Win Rate", "–")
    col3.metric("Avg Win Rate", "–")

if df_bt.empty:
    st.info("No backtests found — run step 2 to generate one.")
else:
    st.dataframe(df_bt, use_container_width=True)
    st.line_chart(df_bt.set_index("run_at")["net_profit"], height=300)

# ─── Live Orders ──────────────────────────────────────────
st.subheader("📈 Live Orders")
@st.cache_data(ttl=REFRESH_MS//1000)
def load_trades(n):
    query = """
      SELECT buy_time   AS timestamp, symbol, 'buy' AS side, qty, buy_price AS price
        FROM trades WHERE buy_time IS NOT NULL
      UNION ALL
      SELECT sell_time AS timestamp, symbol, 'sell' AS side, qty, sell_price AS price
        FROM trades WHERE sell_time IS NOT NULL
      ORDER BY timestamp DESC
      LIMIT %s;
    """
    with psycopg2.connect(DSN) as conn:
        df = pd.read_sql(query, conn, params=(n,))
    return df.set_index("timestamp")

df_live = load_trades(MAX_ROWS)
if df_live.empty:
    st.info("No live trades executed yet.")
else:
    st.dataframe(df_live, use_container_width=True)
    c1, c2 = st.columns(2)
    with c1: st.line_chart(df_live["price"], height=250)
    with c2: st.bar_chart(df_live["qty"],   height=250)

# ─── Environment ──────────────────────────────────────────
st.subheader("🔧 Environment")
env = {
    "Python":      subprocess.run(["python3","--version"], capture_output=True, text=True).stdout.strip(),
    "Liu CLI":     subprocess.run(["liu","--version"], capture_output=True, text=True).stdout.strip(),
    "Streamlit":   subprocess.run(["streamlit","--version"], capture_output=True, text=True).stdout.strip(),
    "Backtests":   len(df_bt),
    "Live Trades": len(df_live),
}
st.json(env)
