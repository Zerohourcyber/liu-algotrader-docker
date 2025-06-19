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
        else:
            try:
                toml.load(tp_toml)
            except Exception as e:
                issues.append(f"Error parsing tradeplan.toml: {e}")

    # 2.3) enhanced_backtest import check
    try:
        importlib.import_module("liualgotrader.enhanced_backtest")
    except Exception as e:
        issues.append(f"Could not import enhanced_backtest: {e}")

    # 2.4) DB tables + batch/trade counts
    if engine:
        insp = inspect(engine)
        # ensure required tables exist
        for tbl in ("algo_run", "trades"):
            if not insp.has_table(tbl):
                issues.append(f"Missing table: {tbl}")

        if insp.has_table("algo_run") and insp.has_table("trades"):
            # fetch latest 10 batches
            runs_df = pd.read_sql(
                """
                SELECT
                  batch_id,
                  COUNT(*) AS run_count
                FROM algo_run
                GROUP BY batch_id
                ORDER BY MAX(start_time) DESC
                LIMIT 10
                """,
                engine,
            )
            for row in runs_df.itertuples(index=False):
                bid = row.batch_id
                rc  = int(row.run_count)

                # count associated trades
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

    return {
        "env":       env,
        "issues":    issues,
        "batches":   batches,
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
    tp_input    = st.text_input("Tradeplan TOML",       value=str(default_tp))
    syms_input  = st.text_input("Symbols (comma-separated)", "AAPL,MSFT,GOOG")
    start_dt    = st.date_input("Start Date",           value=datetime.today())
    end_dt      = st.date_input("End Date",             value=datetime.today())
    batch_input = st.text_input(
                     "Batch ID",
                     value=f"run-{datetime.now():%Y%m%d-%H%M%S}"
                   )
    run_bt      = st.form_submit_button("▶️ Run Backtest")

if run_bt:
    cmd = [
        "python", "-m", "liualgotrader.enhanced_backtest",
        "--tradeplan", tp_input,
        "--symbols",    syms_input,
        "--start-date", start_dt.strftime("%Y-%m-%d"),
        "--end-date",   end_dt.strftime("%Y-%m-%d"),
        "--batch-id",   batch_input,
    ]
    st.info("Running backtest… this may take a minute.")
    st.code(" ".join(cmd), language="bash")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=os.environ,
            cwd=str(Path(tp_input).parent),
        )
        st.subheader("📟 Backtest Output")
        st.text_area(
            "STDOUT & STDERR",
            value=result.stdout + "\n\n" + result.stderr,
            height=300,
        )
        if result.returncode == 0:
            st.success("Backtest completed successfully! ✅")
        else:
            st.error(f"Backtest exited with code {result.returncode}")
    except Exception as e:
        st.exception(f"Error launching backtest: {e}")

    st.warning(
        "Once backtest finishes, click **Run Health Check** to re-validate your tables."
    )
