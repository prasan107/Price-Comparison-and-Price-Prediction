import asyncio
from sqlalchemy import func
from urllib.parse import urlsplit, urlunsplit
from sqlalchemy.orm import Session
from scrapers.amazon import AmazonScraper
from scrapers.flipkart import FlipkartScraper
from scrapers.base import ScrapedProduct
from db.models import Product, PriceRecord
from datetime import datetime, timezone


# Registry — add new scrapers here only, nothing else changes
SCRAPERS = [
    AmazonScraper(),
    FlipkartScraper(),
]


def normalize_product_url(url: str) -> str:
    """
    Strip tracking parameters so the same product listing always
    maps to the same DB row, even if the URL has different ref/qid/lid params.

    Amazon:   keeps only /dp/ASIN  (the stable product identifier)
    Flipkart: keeps scheme + host + path, drops query string
    """
    try:
        parts = urlsplit(url.strip())
        path  = parts.path.rstrip("/") or "/"

        if "amazon." in parts.netloc.lower():
            segments = path.split("/")
            if "dp" in segments:
                idx = segments.index("dp")
                if idx + 1 < len(segments):
                    path = f"/dp/{segments[idx + 1]}"

        return urlunsplit((
            parts.scheme.lower(),
            parts.netloc.lower().removeprefix("www."),
            path,
            "",   # drop query string
            "",   # drop fragment
        ))
    except Exception:
        return url  # fall back to original if parsing fails


async def run_all_scrapers(query: str) -> list[ScrapedProduct]:
    """
    Run all registered scrapers in PARALLEL using asyncio.gather.
    Returns a flat merged list of ScrapedProduct objects.
    """
    tasks = [scraper.search(query) for scraper in SCRAPERS]
    results_per_platform = await asyncio.gather(*tasks, return_exceptions=True)

    merged: list[ScrapedProduct] = []
    for i, result in enumerate(results_per_platform):
        if isinstance(result, Exception):
            print(f"[ScraperService] {SCRAPERS[i].platform_name} failed: {result}")
            continue
        merged.extend(result)

    print(f"[ScraperService] Total products scraped: {len(merged)}")
    return merged


def save_to_db(products: list[ScrapedProduct], db: Session) -> list[Product]:
    """
    Upsert products using NORMALIZED URLs so the same listing always
    maps to the same DB row. Appends a PriceRecord on every scrape —
    this builds the time-series history that Prophet trains on.
    """
    saved: list[Product] = []

    # Load all existing products and build lookup by normalized URL.
    # If multiple rows share the same normalized URL, prefer the one
    # with the most price records (most history accumulated).
    # Product.id.asc() is a deterministic tie-breaker when two rows
    # have the same number of records.
    existing = (
        db.query(Product)
        .outerjoin(PriceRecord)
        .group_by(Product.id)
        .order_by(func.count(PriceRecord.id).desc(), Product.id.asc())
        .all()
    )
    url_lookup: dict[str, Product] = {}
    for p in existing:
        norm = normalize_product_url(p.url)
        if norm not in url_lookup:
            url_lookup[norm] = p   # first seen = most price records

    try:
        for p in products:
            norm_url = normalize_product_url(p.url)
            db_product = url_lookup.get(norm_url)

            if db_product:
                # Reuse the selected existing row.
                db_product.name = p.name
                db_product.image_url = p.image_url
                if p.description:
                    db_product.description = p.description
                db_product.updated_at = datetime.now(timezone.utc)
            else:
                # Create a row only when no normalized URL matches.
                db_product = Product(
                    name=p.name,
                    platform=p.platform,
                    url=p.url,
                    image_url=p.image_url,
                    description=p.description,
                    search_query=p.search_query,
                )
                db.add(db_product)
                db.flush()
                # Cache immediately to prevent duplicates in this batch.
                url_lookup[norm_url] = db_product

            record = PriceRecord(
                product_id=db_product.id,
                price=p.price,
                scraped_at=datetime.now(timezone.utc),
            )
            db.add(record)
            saved.append(db_product)

        db.commit()
        print(f"[ScraperService] Saved {len(saved)} products to DB")
        return saved

    except Exception:
        db.rollback()
        raise