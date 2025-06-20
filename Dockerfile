# Dockerfile.streamlit
FROM python:3.10-slim

# 1) Install Python deps (Liu CLI + Streamlit)
RUN pip install --no-cache-dir \
      liualgotrader \
      streamlit==1.17.0 \
      pandas \
      psycopg2-binary \
      streamlit-autorefresh \
      altair

# 2) Set working dir
WORKDIR /app

# 3) Copy in both Streamlit apps
COPY streamlit/app/dashboard_diagnostics.py .
COPY streamlit/app/live_trades.py           .

# 4) Expose the port used by Streamlit
EXPOSE 8501

# 5) Default command: run diagnostics UI on all interfaces
ENTRYPOINT ["streamlit", "run", "dashboard_diagnostics.py", \
            "--server.port", "8501", "--server.address", "0.0.0.0"]
