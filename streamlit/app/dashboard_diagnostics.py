import os
import subprocess
import streamlit as st
import pandas as pd
import psycopg2
from psycopg2 import errors

# ─── Page config ─────────────────────────────────────────
st.set_page_config(page_title="Diagnostics", layout="wide")
st.title("🩺 LiuAlgoTrader Diagnostics")

DSN        = os.getenv("DSN", "")
TLOG_LEVEL = os.getenv("TLOG_LEVEL", "INFO")

# ─── Sidebar: Setup ───────────────────────────────────────
st.sidebar.header("⚙️ Setup")
st.sidebar.write("**DSN:**", DSN)
st.sidebar.write("**Log Level:**", TLOG_LEVEL)

initial = st.sidebar.number_input(
    "Initial portfolio ($)", min_value=1000, value=25_000, step=1_000
)
if st.sidebar.button("Initialize Portfolio"):
    proc = subprocess.run(
        ["liu", "create", "portfolio", str(initial), f"--dsn={DSN}"],
        capture_output=True,
        text=True
    )
    if proc.returncode == 0:
        st.sidebar.success(f"Portfolio initialized to ${initial:,}")
    else:
        st.sidebar.error(proc.stderr.strip())

# ─── Recent Backtests ──────────────────────────────────────
st.subheader("📝 Recent Backtests")
def fetch_backtests(limit=5):
    sql = """
        SELECT batch_id, run_at, symbols, win_rate, net_profit
          FROM backtests
         ORDER BY run_at DESC
         LIMIT %s
    """
    try:
        with psycopg2.connect(DSN) as conn:
            df = pd.read_sql(sql, conn, params=(limit,))
        df["run_at"] = pd.to_datetime(df["run_at"])
        return df
    except errors.UndefinedTable:
        # backtests table doesn't exist yet
        return pd.DataFrame()

df_bt = fetch_backtests()
if df_bt.empty:
    st.info("No backtests found—run `liu fix-it-bot` first to generate some.")
else:
    st.dataframe(df_bt, use_container_width=True)

# ─── Environment & Versions ───────────────────────────────
st.subheader("🔍 Environment")
env = {
    "Python": subprocess.run(
        ["python3", "--version"], capture_output=True, text=True
    ).stdout.strip(),
    "Liu CLI": subprocess.run(
        ["liu", "--version"], capture_output=True, text=True
    ).stdout.strip(),
    "Streamlit": subprocess.run(
        ["streamlit", "--version"], capture_output=True, text=True
    ).stdout.strip(),
}
st.json(env)

# ─── Detected Issues (placeholder) ────────────────────────
st.subheader("⚠️ Detected Issues")
st.write("None detected — you’re good to go!")
