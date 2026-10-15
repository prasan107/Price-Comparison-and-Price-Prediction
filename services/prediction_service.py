from sqlalchemy.orm import Session
from prediction.features import load_price_history, has_enough_history
from prediction.prophet_model import train_and_forecast, simple_heuristic
from prediction.deal_scorer import score_deal


def get_prediction_for_product(product_id: int, db: Session) -> dict:
    """
    Full prediction pipeline for one product:
      1. Load price history from DB
      2. Run Prophet forecast (or heuristic if insufficient history)
      3. Score the deal
      4. Return combined result for the API

    This is the function the /predict/{product_id} route calls.
    """
    df = load_price_history(product_id, db)

    if df.empty:
        return {
            "product_id": product_id,
            "error": "No price history found for this product.",
        }

    # Run forecast
    if has_enough_history(df, min_records=5):
        forecast = train_and_forecast(df, days_ahead=7)
    else:
        forecast = simple_heuristic(df)

    # Score the deal
    deal = score_deal(df, forecast)

    return {
        "product_id":      product_id,
        "history_points":  len(df),
        "forecast":        forecast,
        "deal":            deal,
    }


def get_history_for_product(product_id: int, db: Session) -> list[dict]:
    """
    Returns price history as a list of {ds, y} dicts for the frontend chart.
    """
    df = load_price_history(product_id, db)
    if df.empty:
        return []
    return df.rename(columns={"ds": "date", "y": "price"}).to_dict(orient="records")
