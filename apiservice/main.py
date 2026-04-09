from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os
import psycopg2

def get_db_connection():
    """Create and return a PostgreSQL database connection."""
    
# Check if all required environment variables for PostgreSQL are set
    required_vars = ["POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables for PostgreSQL: {', '.join(missing_vars)}")

    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        port=os.getenv("POSTGRES_PORT", 5432)  # Default to 5432 if not set
    )

app = FastAPI()

@app.get("/health")
def health_status():
    """Health check endpoint."""
    return {"status": "ok", "message": "API is running"}