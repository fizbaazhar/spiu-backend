FROM python:3.11-bullseye

# Prevent Python from writing .pyc files and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies and Microsoft ODBC Driver 17 for SQL Server
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    gnupg2 \
    apt-transport-https \
    ca-certificates \
    build-essential \
    unixodbc \
    unixodbc-dev && \
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl -fsSL https://packages.microsoft.com/config/debian/11/prod.list -o /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project files
COPY . /app

# Install Python dependencies (no requirements.txt provided)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    gunicorn \
    flask \
    flask-cors \
    flask-socketio \
    eventlet \
    pyodbc \
    apscheduler \
    python-dotenv

# Expose the port Dokploy will route traffic to
EXPOSE 8001

# Optional: configure SQL Server connection via environment (override in Dokploy)
# ENV SQL_SERVER=168.231.118.97 \\
#     SQL_DATABASE=spiu_replica \\
#     SQL_USERNAME=enviro_api \\
#     SQL_PASSWORD=Enviropak123-

# Run the Flask app via Gunicorn using the factory pattern
# Note: 'app:create_app()' calls the factory in app/__init__.py
CMD ["gunicorn", "-w", "1", "-k", "eventlet", "-b", "0.0.0.0:8001", "app:create_app()"]


