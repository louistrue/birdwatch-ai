FROM python:3.11-slim

WORKDIR /tests

# Install test dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-html \
    psycopg2-binary \
    paho-mqtt \
    requests

COPY test_pipeline.py .
COPY requirements.txt .

CMD ["pytest", "test_pipeline.py", "-v", "--html=/test-data/report.html", "--self-contained-html"]
