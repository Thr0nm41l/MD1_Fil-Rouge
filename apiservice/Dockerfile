FROM python:3.12-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py db.py utils.py ./
COPY routers/ routers/
COPY schemas/ schemas/

# Copy trained ML model (build context must be the repo root)
COPY ml/models/ models/

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]