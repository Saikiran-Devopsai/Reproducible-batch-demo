FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (better layer caching -- only reinstalls
# when requirements.txt actually changes, not on every code edit)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY app/ ./

# This is a batch job, not a long-running service:
# the container starts, processes /app/input, writes /app/output, and exits.
ENTRYPOINT ["python", "process_reports.py"]
