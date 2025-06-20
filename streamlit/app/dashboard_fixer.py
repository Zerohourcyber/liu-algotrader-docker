import os
import pandas as pd
import psycopg2
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# ──────────────────────────────────────────────────────────────────────────────
# Configuration from environment
# ──────────────────────────────────────────────────────────────────────────────
DSN                 = os.getenv("DSN")
REFRESH_INTERVAL_MS = int(os.getenv("REFRESH_INTERVAL_MS", 5000))
MAX_ROWS            = int(os.getenv("MAX_ROWS", 50))

# ──────────────────────────────────────────────────────────────────────────────
# Page setup
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Live Orders", layout="wide")
st.title("📈 Live Orders")

# Auto-refresh every REFRESH_INTERVAL_MS milliseconds
st_autorefresh(interval=REFRESH_INTERVAL_MS, key="live")

# ──────────────────────────────────────────────────────────────────────────────
# Data loader with Streamlit’s new @st.cache_data
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=REFRESH_INTERVAL_MS // 1000)
def get_latest_trades(limit: int) -> pd.DataFrame:
    query = """
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
        df = pd.read_sql(query, conn, params=(limit,))
    return df.set_index("timestamp")

# ──────────────────────────────────────────────────────────────────────────────
# Main UI
# ──────────────────────────────────────────────────────────────────────────────
df = get_latest_trades(MAX_ROWS)

if df.empty:
    st.info("No trades have executed yet.")
else:
    st.subheader(f"Last {len(df)} executions")
    st.dataframe(df, use_container_width=True)

    price_series = df["price"]
    qty_series   = df["qty"]

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Price over time")
        st.line_chart(price_series, height=300)
    with col2:
        st.markdown("#### Quantity over time")
        st.bar_chart(qty_series, height=300)
