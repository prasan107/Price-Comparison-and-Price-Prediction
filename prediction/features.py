import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from db.models import PriceRecord


def load_price_history(product_id: int, db: Session) -> pd.DataFrame:
    """
    Load all PriceRecords for a product into a DataFrame.
    Returns columns: ds (datetime), y (price)
    Prophet expects exactly these column names.
    """
    records = (
        db.query(PriceRecord)
        .filter(PriceRecord.product_id == product_id)
        .order_by(PriceRecord.scraped_at.asc())
        .all()
    )

    if not records:
        return pd.DataFrame(columns=["ds", "y"])

    df = pd.DataFrame([
        {"ds": r.scraped_at, "y": r.price}
        for r in records
    ])

    # Prophet needs timezone-naive datetimes
    df["ds"] = pd.to_datetime(df["ds"]).dt.tz_localize(None)
    df["y"]  = df["y"].astype(float)

    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add extra features to the price history DataFrame.
    These are used by the XGBoost deal scorer (not Prophet — Prophet
    handles seasonality internally).

    Features added:
      - rolling_avg_7   : 7-day rolling average
      - rolling_min_7   : 7-day rolling minimum
      - price_pct_rank  : where current price sits in historical range (0=lowest, 1=highest)
      - day_of_week     : 0=Monday … 6=Sunday (weekends sometimes cheaper)
      - is_sale_season  : 1 during Oct–Nov (Diwali) and Jan (Republic Day sale)
      - pct_vs_rolling  : how far current price is from 7-day avg (negative = good deal)
    """
    if df.empty:
        return df

    df = df.copy().sort_values("ds").reset_index(drop=True)

    df["rolling_avg_7"] = df["y"].rolling(window=7, min_periods=1).mean()
    df["rolling_min_7"] = df["y"].rolling(window=7, min_periods=1).min()

    y_min = df["y"].min()
    y_max = df["y"].max()
    df["price_pct_rank"] = (
        (df["y"] - y_min) / (y_max - y_min)
        if y_max > y_min else 0.5
    )

    df["day_of_week"] = df["ds"].dt.dayofweek

    month = df["ds"].dt.month
    df["is_sale_season"] = ((month == 10) | (month == 11) | (month == 1)).astype(int)

    df["pct_vs_rolling"] = (
        (df["y"] - df["rolling_avg_7"]) / df["rolling_avg_7"] * 100
    ).round(2)

    return df


def has_enough_history(df: pd.DataFrame, min_records: int = 5) -> bool:
    """
    Prophet needs at least a few data points to fit meaningfully.
    For a brand-new product with only 1–2 records we return a simple
    heuristic instead of running the model.
    """
    return len(df) >= min_records
