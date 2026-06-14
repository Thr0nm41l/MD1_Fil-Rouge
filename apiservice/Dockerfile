# ==========================================================================
# File must be builded from repo root
# docker build . -f apiservice/Dockerfile -t thronmail/md1-fil-rouge-api:latest --platform linux/amd64,linux/arm64
# ==========================================================================

FROM python:3.12-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY apiservice/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY apiservice/main.py apiservice/db.py apiservice/utils.py ./
COPY apiservice/routers/ routers/
COPY apiservice/schemas/ schemas/
COPY ml/models/ models/

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]