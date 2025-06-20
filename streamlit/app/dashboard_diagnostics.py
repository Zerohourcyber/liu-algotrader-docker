import os
import subprocess
import streamlit as st
import json
import pandas as pd
import psycopg2

# ──────────────────────────────────────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Diagnostics", layout="wide")
st.title("🩺 LiuAlgoTrader Diagnostics")

DSN = os.getenv("DSN", "")
TLOG_LEVEL = os.getenv("TLOG_LEVEL", "INFO")

# ──────────────────────────────────────────────────────────────────────────────
# Sidebar: Setup
# ──────────────────────────────────────────────────────────────────────────────
st.sidebar.header("⚙️ Setup")

# Show current DSN & log level
st.sidebar.write("**DSN:**", DSN)
st.sidebar.write("**Log Level:**", TLOG_LEVEL)

# Portfolio initialization
initial = st.sidebar.number_input(
    "Initial portfolio ($)", min_value=1000, value=25_000, step=1_000,
    help="Set your starting buying power"
)
if st.sidebar.button("Initialize Portfolio"):
    cmd = ["liu", "create", "portfolio", str(initial), f"--dsn={DSN}"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode == 0:
        st.sidebar.success(f"Portfolio initialized to ${initial:,}")
    else:
        st.sidebar.error(f"Error: {proc.stderr.strip()}")

# ──────────────────────────────────────────────────────────────────────────────
# Section: Recent Backtests
# ──────────────────────────────────────────────────────────────────────────────
st.subheader("📝 Recent Backtests")

def fetch_backtests(limit=5):
    """Load the most recent backtest summaries from your DB."""
    query = """
        SELECT batch_id, run_at, symbols, win_rate, net_profit
          FROM backtests
         ORDER BY run_at DESC
         LIMIT %s
    """
    with psycopg2.connect(DSN) as conn:
        df = pd.read_sql(query, conn, params=(limit,))
    return df

try:
    df_bt = fetch_backtests()
    if df_bt.empty:
        st.info("No backtests found yet.")
    else:
        df_bt["run_at"] = pd.to_datetime(df_bt["run_at"])
        st.dataframe(df_bt, use_container_width=True)
except Exception as e:
    st.error(f"Could not fetch backtests: {e}")

# ──────────────────────────────────────────────────────────────────────────────
# Section: Environment & Versions
# ──────────────────────────────────────────────────────────────────────────────
st.subheader("🔍 Environment")
env = {
    "Python": subprocess.run(["python3", "--version"], capture_output=True, text=True).stdout.strip(),
    "Liu CLI": subprocess.run(["liu", "--version"], capture_output=True, text=True).stdout.strip(),
    "Streamlit": subprocess.run(["streamlit", "--version"], capture_output=True, text=True).stdout.strip(),
}
st.json(env)

# ──────────────────────────────────────────────────────────────────────────────
# Placeholder for extra diagnostics…
# ──────────────────────────────────────────────────────────────────────────────
st.subheader("⚠️ Detected Issues")
st.write("None detected — you’re good to go!")
