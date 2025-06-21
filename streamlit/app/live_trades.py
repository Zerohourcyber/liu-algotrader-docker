import os
import pandas as pd
import psycopg2
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# ─── Page config & styling ─────────────────────────────────
st.set_page_config(
    page_title="Live Orders",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("📈 Live Orders")
st.write("---")

# ─── Environment vars ───────────────────────────────────────
DSN                 = os.getenv("DSN", "")
REFRESH_INTERVAL_MS = int(os.getenv("REFRESH_INTERVAL_MS", 5000))
MAX_ROWS            = int(os.getenv("MAX_ROWS", 50))

# ─── Auto-refresh ───────────────────────────────────────────
st_autorefresh(interval=REFRESH_INTERVAL_MS, key="live_orders")

# ─── Sidebar controls ───────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    st.write("**DSN:**", DSN or "not set")
    st.write("**Refresh (ms):**", REFRESH_INTERVAL_MS)
    rows = st.slider("Max rows to show", 10, 200, MAX_ROWS, step=10)
    st.write("---")

# ─── Data loading ────────────────────────────────────────────
@st.cache_data(ttl=REFRESH_INTERVAL_MS // 1000)
def get_latest_trades(limit: int) -> pd.DataFrame:
    sql = """
        SELECT buy_time   AS timestamp,
               symbol,
               'buy'      AS side,
               qty,
               buy_price AS price
          FROM trades
         WHERE buy_time IS NOT NULL
        UNION ALL
        SELECT sell_time  AS timestamp,
               symbol,
               'sell'     AS side,
               qty,
               sell_price AS price
          FROM trades
         WHERE sell_time IS NOT NULL
        ORDER BY timestamp DESC
        LIMIT %s
    """
    with psycopg2.connect(DSN) as conn:
        df = pd.read_sql(sql, conn, params=(limit,))
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.set_index("timestamp")

df = get_latest_trades(rows)

# ─── Main content ───────────────────────────────────────────
if df.empty:
    st.info("No trades have executed yet. Waiting for live data…")
else:
    st.subheader(f"Showing last {len(df)} executions")
    
    # Table of recent trades
    st.dataframe(df, use_container_width=True)
    
    # Split into two charts
    price_chart, qty_chart = st.columns(2)
    with price_chart:
        st.markdown("#### Price over Time")
        st.line_chart(df["price"], height=300)
    with qty_chart:
        st.markdown("#### Quantity over Time")
        st.bar_chart(df["qty"], height=300)
