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
st.set_page_config(page_title="LiuAlgoTrader Diagnostics", layout="wide")
st.title("🔍 LiuAlgoTrader Environment Diagnostics")

# ————— Sidebar: Run Health Check button —————
if "health_check" not in st.session_state:
    st.session_state.health_check = True
if st.sidebar.button("🔄 Run Health Check"):
    st.session_state.health_check = True

# ————— 1) Environment Variables —————
required_env = ["DSN", "TRADEPLAN_DIR", "TLOG_LEVEL"]
env = {k: os.getenv(k, "") for k in required_env}

st.subheader("📦 Environment Variables")
env_df = pd.DataFrame(list(env.items()), columns=["Variable", "Value"]).set_index("Variable")
st.table(env_df)

# ————— 2a) Cache a single DB engine instance —————
@st.cache_resource
def get_engine(dsn: str):
    return create_engine(dsn)

# ————— 2b) Diagnostics logic —————
@st.cache_data(ttl=0)
def collect_diagnostics(env: dict):
    issues = []
    batches = []
    backtests = []

    # 2.1) DSN check
    dsn = env["DSN"]
    engine = None
    if not dsn:
        issues.append("DSN not set")
    else:
        try:
            engine = get_engine(dsn)
            with engine.connect():
                pass  # simple round‐trip
        except Exception as e:
            issues.append(f"DSN connection error: {e}")

    # 2.2) TRADEPLAN_DIR + TOML parse
    tp_dir = env["TRADEPLAN_DIR"]
    if not tp_dir:
        issues.append("TRADEPLAN_DIR not set")
    else:
        tp = Path(tp_dir)
        tp_toml = tp / "tradeplan.toml"
        if not tp.exists():
            issues.append(f"TRADEPLAN_DIR does not exist: {tp}")
        elif not tp_toml.exists():
            issues.append(f"tradeplan.toml not found in {tp}")
@@ -105,77 +106,109 @@ def collect_diagnostics(env: dict):
                tc = engine.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM trades t
                          JOIN algo_run ar
                            ON t.algo_run_id = ar.algo_run_id
                         WHERE ar.batch_id = :bid
                        """
                    ),
                    {"bid": bid},
                ).scalar() or 0

                batches.append({
                    "batch_id":    bid,
                    "run_count":   rc,
                    "trade_count": int(tc),
                })

                # flag duplicates
                if rc > 1:
                    issues.append(f"batch_id '{bid}' appears {rc}×")
                # flag empty runs
                if tc == 0:
                    issues.append(f"No trades found for batch_id '{bid}'")

        # optional backtests table
        if insp.has_table("backtests"):
            try:
                bt_df = pd.read_sql(
                    """
                    SELECT batch_id,
                           run_at,
                           symbols,
                           win_rate,
                           net_profit
                      FROM backtests
                     ORDER BY run_at DESC
                     LIMIT 5
                    """,
                    engine,
                )
                backtests = bt_df.to_dict("records")
            except Exception as e:
                issues.append(f"Error reading backtests: {e}")
        else:
            issues.append("Missing table: backtests")

    return {
        "env":       env,
        "issues":    issues,
        "batches":   batches,
        "backtests": backtests,
        "timestamp": datetime.utcnow().isoformat(),
    }

# ————— 3) Display diagnostics if needed —————
if st.session_state.health_check:
    diag = collect_diagnostics(env)

    st.subheader("🕒 Recent Batch IDs (with run_count / trade_count)")
    if diag["batches"]:
        st.dataframe(
            pd.DataFrame(diag["batches"]),
            use_container_width=True
        )
    else:
        st.info("No batches found in algo_run.")

    st.subheader("🚨 Detected Issues")
    if diag["issues"]:
        for i, issue in enumerate(diag["issues"], 1):
            st.error(f"{i}. {issue}")
    else:
        st.success("No issues detected! 🎉")

    st.subheader("📝 Recent Backtests")
    if diag.get("backtests"):
        st.dataframe(
            pd.DataFrame(diag["backtests"]),
            use_container_width=True
        )
    else:
        st.info("No backtests found (or table is missing).")

    # write out diagnostics.json
    out_path = Path(__file__).parent / "diagnostics.json"
    with open(out_path, "w") as f:
        json.dump(diag, f, indent=2)
    st.caption(f"Diagnostics written to `{out_path}`")

    # download button
    with open(out_path, "rb") as f:
        st.download_button(
            label="📥 Download diagnostics.json",
            data=f,
            file_name="diagnostics.json",
            mime="application/json",
        )

    # reset the flag until next click
    st.session_state.health_check = False

# ————— Sidebar: ⚡ Run Backtest —————
st.sidebar.markdown("---")
st.sidebar.header("⚡ Run Backtest")

default_tp = Path(env.get("TRADEPLAN_DIR", ".")) / "tradeplan.toml"

with st.sidebar.form("run_backtest", clear_on_submit=False):