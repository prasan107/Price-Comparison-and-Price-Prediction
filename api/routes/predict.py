from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from services.prediction_service import get_prediction_for_product, get_history_for_product

router = APIRouter()


@router.get("/predict/{product_id}")
def predict(product_id: int, db: Session = Depends(get_db)):
    """
    Returns Prophet 7-day forecast + deal score for a product.
    Needs at least 5 price records in DB — run a few searches first.
    """
    return get_prediction_for_product(product_id, db)


@router.get("/history/{product_id}")
def history(product_id: int, db: Session = Depends(get_db)):
    """
    Returns the full price history as [{date, price}] for Recharts.
    """
    data = get_history_for_product(product_id, db)
    if not data:
        return {"error": "No price history found", "data": []}
    return {"product_id": product_id, "data": data}
