import os
import subprocess
import streamlit as st

st.set_page_config(page_title="Diagnostics", layout="wide")
st.title("🩺 LiuAlgoTrader Diagnostics")

# ─────── Sidebar: Setup ───────
st.sidebar.header("⚙️ Setup")
initial = st.sidebar.number_input(
    "Initial portfolio ($)", min_value=1000, value=25000, step=1000
)
if st.sidebar.button("Initialize Portfolio"):
    DSN = os.environ["DSN"]
    cmd = ["liu", "create", "portfolio", str(initial), f"--dsn={DSN}"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode == 0:
        st.sidebar.success(f"Portfolio set to ${initial:,}")
    else:
        st.sidebar.error(proc.stderr)

# ─────── rest of your existing diagnostics code follows here ───────
# e.g. show environment vars, recent backtests, detected issues…
