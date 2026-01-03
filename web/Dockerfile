FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY templates/ templates/

# Create static directories
RUN mkdir -p /app/static/snapshots /app/static/recordings

# Expose port
EXPOSE 8080

# Run the web app
CMD ["python", "-u", "app.py"]
