# engine-wrapper/dashboard_fixer.py
import os
import subprocess
import json
from datetime import datetime
from pathlib import Path

import streamlit as st
import toml
import importlib
import pandas as pd
from sqlalchemy import create_engine, inspect, text

# ————— Page config —————
st.set_page_config(page_title="LiuAlgoTrader Fixer", layout="wide")
st.title("🔧 LiuAlgoTrader Environment & Data Fixer")

# ————— Load diagnostics.json (auto-refresh on re-run) —————
diag_path = Path(__file__).parent / "diagnostics.json"
if diag_path.exists():
    diagnostics = json.loads(diag_path.read_text())
else:
    st.error("No diagnostics.json found — run the Diagnostics app first.")
    st.stop()

# ————— Fix Summary —————
st.subheader("📋 Fix Summary")
for i, issue in enumerate(diagnostics["issues"], start=1):
    st.warning(f"{i}. {issue}")

st.markdown("---")
st.markdown("### Workflow")
st.markdown(
    """
1. Run Diagnostics → download `diagnostics.json`  
2. Switch here, overwrite `diagnostics.json` (auto-loaded)  
3. Apply fixes below  
4. Re-run Diagnostics to confirm!  
"""
)

# ————— Sidebar: Environment Editor —————
st.sidebar.header("⚙️ Environment Editor")
env = diagnostics["env"]

dsn_in   = st.sidebar.text_input("Postgres DSN",    value=env.get("DSN",""))
tpdir_in = st.sidebar.text_input("TRADEPLAN_DIR",    value=env.get("TRADEPLAN_DIR",""))
tlog_in  = st.sidebar.selectbox(
    "TLOG_LEVEL", ["DEBUG","INFO","WARN","ERROR"], index=["DEBUG","INFO","WARN","ERROR"].index(env.get("TLOG_LEVEL","DEBUG"))
)
if st.sidebar.button("💾 Save ENV to ~/.bashrc"):
    bashrc = Path.home()/".bashrc"
    lines = bashrc.read_text().splitlines()
    # remove old exports
    lines = [l for l in lines if not l.startswith(("export DSN=","export TRADEPLAN_DIR=","export TLOG_LEVEL="))]
    # append new
    lines += [
        f'export DSN="{dsn_in}"',
        f'export TRADEPLAN_DIR="{tpdir_in}"',
        f'export TLOG_LEVEL="{tlog_in}"',
    ]
    bashrc.write_text("\n".join(lines)+"\n")
    st.sidebar.success("✅ Wrote to ~/.bashrc — open a new shell to pick up.")

st.sidebar.markdown("---")

# ————— Duplicate Batch Cleanup —————
st.subheader("🗑️ Duplicate Batch Cleanup")
batches = pd.DataFrame(diagnostics["batches"])
dupes = batches.loc[batches["run_count"] > 1]
if not dupes.empty:
    st.table(dupes)
    pick = st.selectbox("Pick batch_id to dedupe", dupes["batch_id"].tolist())
    if st.button("🗑️ Remove old duplicates"):
        try:
            engine = create_engine(env["DSN"])
            delete_sql = text("""
                -- delete dependent trades first
                DELETE FROM trades
                 WHERE algo_run_id IN (
                   SELECT algo_run_id
                     FROM algo_run
                    WHERE batch_id = :bid
                      AND algo_run_id <> (
                        SELECT MAX(algo_run_id)
                          FROM algo_run
                         WHERE batch_id = :bid
                      )
                 );
                -- then remove old algo_run entries
                DELETE FROM algo_run
                 WHERE batch_id = :bid
                   AND algo_run_id <> (
                     SELECT MAX(algo_run_id)
                       FROM algo_run
                      WHERE batch_id = :bid
                   );
            """)
            with engine.begin() as conn:
                conn.execute(delete_sql, {"bid": pick})
            st.success(f"Cleaned duplicates for {pick}")
        except Exception as e:
            st.error(f"Failed to clean duplicates: {e}")
else:
    st.info("No duplicate batch_ids detected.")

st.markdown("---")

# ————— Tradeplan Editor —————
st.subheader("📝 Tradeplan Editor")
tp_path = Path(tpdir_in) / "tradeplan.toml"
if tp_path.exists():
    content = tp_path.read_text()
else:
    content = "# tradeplan.toml not found at " + str(tp_path)
new_content = st.text_area("Edit tradeplan.toml", content, height=300)
if st.button("💾 Save tradeplan.toml"):
    try:
        tp_path.write_text(new_content)
        st.success("Saved tradeplan.toml!")
    except Exception as e:
        st.error(f"Failed to save TOML: {e}")

st.markdown("---")

# ————— Sidebar: ⚡ Run Backtest —————
st.sidebar.header("⚡ Run Backtest")
default_tp = tp_path
with st.sidebar.form("run_backtest", clear_on_submit=False):
    tp_in    = st.text_input("Tradeplan TOML", str(default_tp))
    syms_in  = st.text_input("Symbols (comma-separated)", "AAPL,MSFT,GOOG")
    dt0      = st.date_input("Start Date", datetime.today())
    dt1      = st.date_input("End Date",   datetime.today())
    batch_in = st.text_input("Batch ID", f"run-{datetime.now():%Y%m%d-%H%M%S}")
    go_bt    = st.form_submit_button("▶️ Run Backtest")

if go_bt:
    cmd = [
        "python", "-m", "liualgotrader.enhanced_backtest",
        "--tradeplan", tp_in,
        "--symbols",  syms_in,
        "--start-date", dt0.strftime("%Y-%m-%d"),
        "--end-date",   dt1.strftime("%Y-%m-%d"),
        "--batch-id",   batch_in,
    ]
    st.info("Running backtest… this may take a minute.")
    st.code(" ".join(cmd), language="bash")
    try:
        res = subprocess.run(cmd, capture_output=True, text=True,
                             env=os.environ,
                             cwd=str(Path(tp_in).parent))
        st.subheader("📟 Backtest Output")
        st.text_area("STDOUT & STDERR",
                     value=res.stdout + "\n\n" + res.stderr,
                     height=300)
        if res.returncode == 0:
            st.success("Backtest completed successfully! ✅")
        else:
            st.error(f"Backtest exited with code {res.returncode}")
    except Exception as e:
        st.exception(f"Error launching backtest: {e}")
    st.warning("When it’s done, click **Run Diagnostics** in the other app to re-validate tables.")
