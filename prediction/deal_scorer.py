import numpy as np
import pandas as pd
from prediction.features import engineer_features


def score_deal(df: pd.DataFrame, forecast: dict) -> dict:
    """
    Rule-based deal scorer that becomes XGBoost-trainable once you have
    enough labelled data (label = did price drop further after this point?).

    Right now uses weighted scoring rules — fully explainable in an interview.
    Replace score_deal_xgboost() below once you have 100+ labelled samples.

    Returns:
        {
          "score":   int (0-100),
          "verdict": "Excellent" | "Good" | "Wait",
          "reasons": [str, ...]   ← shown in UI tooltip
        }
    """
    if df.empty or not forecast:
        return {"score": 50, "verdict": "Wait", "reasons": ["Insufficient data"]}

    df_feat = engineer_features(df)
    latest  = df_feat.iloc[-1]

    score   = 50   # neutral baseline
    reasons = []

    # --- Rule 1: Price vs rolling 7-day average (+/- 20 pts) ---
    pct_vs_rolling = latest.get("pct_vs_rolling", 0)
    if pct_vs_rolling <= -10:
        score += 20
        reasons.append(f"Price is {abs(pct_vs_rolling):.1f}% below 7-day average")
    elif pct_vs_rolling <= -5:
        score += 10
        reasons.append(f"Price is {abs(pct_vs_rolling):.1f}% below 7-day average")
    elif pct_vs_rolling >= 10:
        score -= 20
        reasons.append(f"Price is {pct_vs_rolling:.1f}% above 7-day average — may drop soon")
    elif pct_vs_rolling >= 5:
        score -= 10
        reasons.append(f"Price is {pct_vs_rolling:.1f}% above 7-day average")

    # --- Rule 2: Price percentile in historical range (+/- 20 pts) ---
    pct_rank = latest.get("price_pct_rank", 0.5)
    if pct_rank <= 0.15:
        score += 20
        reasons.append("Near all-time low price — great time to buy")
    elif pct_rank <= 0.35:
        score += 10
        reasons.append("Price is in the lower range historically")
    elif pct_rank >= 0.85:
        score -= 20
        reasons.append("Near all-time high — consider waiting")
    elif pct_rank >= 0.65:
        score -= 10
        reasons.append("Price is in the upper range historically")

    # --- Rule 3: Forecast trend (+/- 15 pts) ---
    trend     = forecast.get("trend", "stable")
    trend_pct = forecast.get("trend_pct", 0)
    if trend == "drop":
        score -= 15
        reasons.append(f"Forecast: price may drop {abs(trend_pct):.1f}% in 7 days — consider waiting")
    elif trend == "rise":
        score += 15
        reasons.append(f"Forecast: price may rise {trend_pct:.1f}% in 7 days — buy now")

    # --- Rule 4: Sale season bonus (+10 pts) ---
    if latest.get("is_sale_season", 0) == 1:
        score += 10
        reasons.append("Sale season (Diwali / Republic Day) — prices likely at seasonal low")

    # Clamp score to 0-100
    score = int(np.clip(score, 0, 100))

    if score >= 75:
        verdict = "Excellent"
    elif score >= 50:
        verdict = "Good"
    else:
        verdict = "Wait"

    return {
        "score":   score,
        "verdict": verdict,
        "reasons": reasons,
    }
