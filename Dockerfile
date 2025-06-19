# Dockerfile
FROM python:3.10-slim

# 1) install the Liu CLI + Streamlit
RUN pip install --no-cache-dir liualgotrader streamlit

WORKDIR /app

# 2) copy in your Streamlit apps
COPY streamlit/app/ . 

# 3) expose Streamlit’s port
EXPOSE 8501

# 4) launch the diagnostics UI
ENTRYPOINT ["streamlit", "run", "dashboard_diagnostics.py", \
            "--server.port", "8501", "--server.address", "0.0.0.0"]
