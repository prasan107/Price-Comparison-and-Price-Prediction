from sqlalchemy.orm import Session
from db.models import Product, PriceRecord
from sqlalchemy import func


def get_latest_price(product_id: int, db: Session) -> float | None:
    """Get the most recently scraped price for a product."""
    record = (
        db.query(PriceRecord)
        .filter(PriceRecord.product_id == product_id)
        .order_by(PriceRecord.scraped_at.desc())
        .first()
    )
    return record.price if record else None


def get_price_stats(product_id: int, db: Session) -> dict:
    """
    Returns min, max, avg price over all stored history for this product.
    Used by the deal scorer and comparison view.
    """
    stats = db.query(
        func.min(PriceRecord.price).label("min_price"),
        func.max(PriceRecord.price).label("max_price"),
        func.avg(PriceRecord.price).label("avg_price"),
        func.count(PriceRecord.id).label("record_count"),
    ).filter(PriceRecord.product_id == product_id).first()

    return {
        "min_price":    round(stats.min_price, 2)   if stats.min_price else None,
        "max_price":    round(stats.max_price, 2)   if stats.max_price else None,
        "avg_price":    round(stats.avg_price, 2)   if stats.avg_price else None,
        "record_count": stats.record_count or 0,
    }


def build_comparison_result(products: list[Product], db: Session) -> dict:
    """
    Given a list of Product rows (from one search),
    return a structured comparison dict with:
      - all products ranked by current price (cheapest first)
      - best value pick (cheapest with enough history)
      - per-platform cheapest
    """
    enriched = []
    for p in products:
        current_price = get_latest_price(p.id, db)
        if current_price is None:
            continue
        stats = get_price_stats(p.id, db)

        # Price vs average — negative means currently below average (good deal)
        avg = stats["avg_price"] or current_price
        pct_vs_avg = round(((current_price - avg) / avg) * 100, 1)

        enriched.append({
            "product_id":   p.id,
            "name":         p.name,
            "platform":     p.platform,
            "url":          p.url,
            "image_url":    p.image_url,
            "description":  p.description,
            "current_price": current_price,
            "min_price":    stats["min_price"],
            "max_price":    stats["max_price"],
            "avg_price":    stats["avg_price"],
            "record_count": stats["record_count"],
            "pct_vs_avg":   pct_vs_avg,   # negative = good, positive = expensive
        })

    if not enriched:
        return {"products": [], "best_value": None, "by_platform": {}}

    # Sort cheapest first
    enriched.sort(key=lambda x: x["current_price"])

    # Best value = cheapest product that has at least 2 price records
    best_value = next(
        (p for p in enriched if p["record_count"] >= 2),
        enriched[0]  # fallback to cheapest if no history yet
    )

    # Cheapest per platform
    by_platform: dict[str, dict] = {}
    for p in enriched:
        platform = p["platform"]
        if platform not in by_platform:
            by_platform[platform] = p   # first = cheapest (already sorted)

    return {
        "products":   enriched,
        "best_value": best_value,
        "by_platform": by_platform,
    }