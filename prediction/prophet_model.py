import pandas as pd
import numpy as np
from prophet import Prophet


def _safe_float(value, default=0.0):
    """Convert a value to float safely."""
    try:
        value = float(value)

        if np.isfinite(value):
            return value

    except (TypeError, ValueError):
        pass

    return float(default)


def _prepare_daily_history(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert raw scrape history into one robust price observation per day.

    Multiple scrapes can happen on the same day. Using the median prevents
    repeated identical scrapes from giving that day excessive weight.
    """

    if df is None or df.empty:
        return pd.DataFrame(columns=["ds", "y"])

    data = df.copy()

    if "ds" not in data.columns or "y" not in data.columns:
        return pd.DataFrame(columns=["ds", "y"])

    data["ds"] = pd.to_datetime(data["ds"], errors="coerce")
    data["y"] = pd.to_numeric(data["y"], errors="coerce")

    data = data.dropna(subset=["ds", "y"])

    if data.empty:
        return pd.DataFrame(columns=["ds", "y"])

    data = data[data["y"] > 0].copy()

    if data.empty:
        return pd.DataFrame(columns=["ds", "y"])

    # Remove timezone information if present.
    try:
        data["ds"] = data["ds"].dt.tz_localize(None)
    except TypeError:
        pass

    # Convert timestamps to calendar dates.
    data["day"] = data["ds"].dt.normalize()

    # One robust price observation per day.
    daily = (
        data.groupby("day", as_index=False)["y"]
        .median()
        .rename(columns={"day": "ds"})
    )

    daily = daily.sort_values("ds").reset_index(drop=True)

    return daily[["ds", "y"]]


def _fallback_forecast(
    daily: pd.DataFrame,
    days_ahead: int,
) -> dict:
    """
    Stable fallback forecast for sparse or unreliable histories.
    """

    prices = daily["y"].astype(float).to_numpy()

    if len(prices) == 0:
        return {
            "forecast": [],
            "current_price": 0.0,
            "predicted_price": 0.0,
            "lower_bound": 0.0,
            "upper_bound": 0.0,
            "trend": "stable",
            "trend_pct": 0.0,
            "mae": 0.0,
        }

    current_price = float(prices[-1])

    recent_count = min(5, len(prices))
    recent_prices = prices[-recent_count:]

    recent_median = float(np.median(recent_prices))
    historical_median = float(np.median(prices))
    historical_min = float(np.min(prices))
    historical_max = float(np.max(prices))

    # Give recent prices more importance.
    target_price = (
        recent_median * 0.70
        + historical_median * 0.30
    )

    # Keep the forecast inside a reasonable historical envelope.
    lower_limit = historical_min * 0.90
    upper_limit = historical_max * 1.10

    target_price = float(
        np.clip(
            target_price,
            lower_limit,
            upper_limit,
        )
    )

    last_date = pd.to_datetime(
        daily["ds"].iloc[-1]
    )

    forecast = []

    for day in range(1, days_ahead + 1):

        progress = min(
            day / max(days_ahead, 1),
            1.0,
        )

        predicted = (
            current_price * (1.0 - progress)
            + target_price * progress
        )

        spread = max(
            abs(historical_max - historical_min) * 0.10,
            current_price * 0.03,
        )

        lower = max(
            predicted - spread,
            historical_min * 0.85,
        )

        upper = min(
            predicted + spread,
            historical_max * 1.15,
        )

        forecast.append(
            {
                "ds": (
                    last_date
                    + pd.Timedelta(days=day)
                ).isoformat(),

                "yhat": round(
                    float(predicted),
                    2,
                ),

                "yhat_lower": round(
                    float(lower),
                    2,
                ),

                "yhat_upper": round(
                    float(upper),
                    2,
                ),
            }
        )

    predicted_price = float(
        forecast[-1]["yhat"]
    )

    trend_pct = (
        (
            predicted_price
            - current_price
        )
        / current_price
        * 100
        if current_price
        else 0.0
    )

    if trend_pct > 3:
        trend = "rise"
    elif trend_pct < -3:
        trend = "fall"
    else:
        trend = "stable"

    return {
        "forecast": forecast,
        "current_price": round(
            current_price,
            2,
        ),
        "predicted_price": round(
            predicted_price,
            2,
        ),
        "lower_bound": round(
            forecast[-1]["yhat_lower"],
            2,
        ),
        "upper_bound": round(
            forecast[-1]["yhat_upper"],
            2,
        ),
        "trend": trend,
        "trend_pct": round(
            float(trend_pct),
            2,
        ),
        "mae": 0.0,
    }


def simple_heuristic(
    df: pd.DataFrame,
) -> dict:
    """
    Simple price heuristic used when there is not enough history
    for Prophet.

    This function is kept because prediction_service.py imports it.
    """

    daily = _prepare_daily_history(df)

    return _fallback_forecast(
        daily,
        days_ahead=7,
    )


def train_and_forecast(
    df: pd.DataFrame,
    days_ahead: int = 7,
) -> dict:
    """
    Train Prophet on daily aggregated price history and forecast
    the next `days_ahead` days.

    Multiple scrapes from the same calendar day are first combined
    using the daily median.

    For sparse histories, simple_heuristic() is used instead.
    """

    daily = _prepare_daily_history(df)

    if daily.empty:
        return simple_heuristic(df)

    current_price = float(
        daily["y"].iloc[-1]
    )

    # Too few unique days for reliable Prophet modelling.
    if len(daily) < 8:
        return simple_heuristic(df)

    try:

        model = Prophet(
            growth="linear",
            weekly_seasonality=False,
            daily_seasonality=False,
            yearly_seasonality=False,
            seasonality_mode="additive",
            changepoint_prior_scale=0.01,
            interval_width=0.90,
        )

        model.fit(daily)

        future = model.make_future_dataframe(
            periods=days_ahead,
            freq="D",
        )

        forecast_df = model.predict(future)

        future_forecast = forecast_df.tail(
            days_ahead
        ).copy()

        historical_min = float(
            daily["y"].min()
        )

        historical_max = float(
            daily["y"].max()
        )

        historical_median = float(
            daily["y"].median()
        )

        # Shopping prices should not be allowed to explode
        # into absurd predictions.
        lower_limit = max(
            historical_min * 0.85,
            historical_median * 0.65,
        )

        upper_limit = min(
            historical_max * 1.15,
            current_price * 1.35,
            historical_median * 1.35,
        )

        # Make sure the limits are valid.
        if upper_limit <= lower_limit:
            return simple_heuristic(df)

        predictions = []

        for _, row in future_forecast.iterrows():

            yhat = _safe_float(
                row["yhat"],
                current_price,
            )

            yhat_lower = _safe_float(
                row["yhat_lower"],
                yhat,
            )

            yhat_upper = _safe_float(
                row["yhat_upper"],
                yhat,
            )

            yhat = float(
                np.clip(
                    yhat,
                    lower_limit,
                    upper_limit,
                )
            )

            yhat_lower = float(
                np.clip(
                    yhat_lower,
                    lower_limit,
                    yhat,
                )
            )

            yhat_upper = float(
                np.clip(
                    yhat_upper,
                    yhat,
                    upper_limit,
                )
            )

            predictions.append(
                {
                    "ds": pd.to_datetime(
                        row["ds"]
                    ).isoformat(),

                    "yhat": round(
                        yhat,
                        2,
                    ),

                    "yhat_lower": round(
                        yhat_lower,
                        2,
                    ),

                    "yhat_upper": round(
                        yhat_upper,
                        2,
                    ),
                }
            )

        if not predictions:
            return simple_heuristic(df)

        predicted_price = float(
            predictions[-1]["yhat"]
        )

        trend_pct = (
            (
                predicted_price
                - current_price
            )
            / current_price
            * 100
            if current_price
            else 0.0
        )

        if trend_pct > 3:
            trend = "rise"
        elif trend_pct < -3:
            trend = "fall"
        else:
            trend = "stable"

        # Calculate training MAE.
        mae = 0.0

        try:

            historical_prediction = model.predict(
                daily[["ds"]]
            )

            fitted = historical_prediction[
                "yhat"
            ].to_numpy()

            actual = daily[
                "y"
            ].to_numpy()

            count = min(
                len(fitted),
                len(actual),
            )

            if count > 0:
                mae = float(
                    np.mean(
                        np.abs(
                            actual[:count]
                            - fitted[:count]
                        )
                    )
                )

        except Exception:
            mae = 0.0

        return {
            "forecast": predictions,

            "current_price": round(
                current_price,
                2,
            ),

            "predicted_price": round(
                predicted_price,
                2,
            ),

            "lower_bound": round(
                predictions[-1]["yhat_lower"],
                2,
            ),

            "upper_bound": round(
                predictions[-1]["yhat_upper"],
                2,
            ),

            "trend": trend,

            "trend_pct": round(
                float(trend_pct),
                2,
            ),

            "mae": round(
                float(mae),
                2,
            ),
        }

    except Exception as error:

        print(
            f"[Prophet] Forecast failed: {error}"
        )

        print(
            "[Prophet] Using heuristic fallback."
        )

        return simple_heuristic(df)