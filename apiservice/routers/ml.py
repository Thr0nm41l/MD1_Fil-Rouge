from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class PredictRequest(BaseModel):
    container_id: int
    horizon_hours: int = 24


@router.post("/predict")
def predict_fill_rate(body: PredictRequest):
    """
    Predict fill rate at a future horizon.
    Requires a trained model file — complete ML1–ML4 notebook pipeline first.
    """
    raise HTTPException(
        status_code=503,
        detail="ML model not yet trained. Run the ML1–ML4 notebooks to produce a model artefact, "
               "then mount it and update this endpoint to load it.",
    )
