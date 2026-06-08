FROM python:3.9-slim

WORKDIR /app

# Install deps first so the layer is cached when only source changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source modules, then the data + config.
COPY src ./src
COPY run.py ./
COPY config.yaml data.csv ./

CMD ["python", "run.py", "--input", "data.csv", "--config", "config.yaml", "--output", "metrics.json", "--log-file", "run.log"]
