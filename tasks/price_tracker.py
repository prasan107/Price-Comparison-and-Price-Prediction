import asyncio
import re
from tasks.celery_app import celery_app
from db.database import SessionLocal
from db.models import Product, PriceRecord
from scrapers.amazon import AmazonScraper
from scrapers.flipkart import FlipkartScraper
from datetime import datetime, timezone


PLATFORM_SCRAPERS = {
    "amazon":   AmazonScraper(),
    "flipkart": FlipkartScraper(),
}


def extract_stable_id(url: str, platform: str) -> str | None:
    """
    Extract the part of a product URL that stays constant across scrapes,
    ignoring volatile tracking params (ref, qid, sr, lid, iid, ssid, etc.)
    that change depending on search result position / session.
    """
    if not url:
        return None
    if platform == "amazon":
        # Amazon ASIN: appears after /dp/ as a 10-char alphanumeric code
        m = re.search(r"/dp/([A-Z0-9]{10})", url)
        return m.group(1) if m else None
    if platform == "flipkart":
        # Flipkart item id: appears after /p/ as itmXXXXXXXX
        m = re.search(r"/p/(itm[a-zA-Z0-9]+)", url)
        return m.group(1) if m else None
    return None


@celery_app.task(name="tasks.price_tracker.scrape_all_tracked")
def scrape_all_tracked():
    """
    Celery Beat calls this every hour.
    Re-scrapes every UNIQUE search query (not every product row) to keep
    price history growing — many products share the same original query,
    so grouping avoids re-searching Amazon/Flipkart 10-20x for the same term.
    """
    db = SessionLocal()
    try:
        products = db.query(Product).all()
        print(f"[PriceTracker] Tracking {len(products)} products")

        # Group products by (platform, search_query) so each unique query
        # is scraped exactly once, then matched against all products that share it
        groups: dict[tuple[str, str], list[Product]] = {}
        for product in products:
            query = product.search_query or product.name
            key = (product.platform, query)
            groups.setdefault(key, []).append(product)

        print(f"[PriceTracker] {len(groups)} unique (platform, query) groups to scrape "
              f"(was {len(products)} individual products)")

        for (platform, query), group_products in groups.items():
            scraper = PLATFORM_SCRAPERS.get(platform)
            if not scraper:
                continue

            try:
                # One search covers every product in this group
                results = asyncio.run(scraper.search(query))
                print(f"[PriceTracker] Scraped '{query}' on {platform} → {len(results)} results, "
                      f"matching against {len(group_products)} tracked products")

                for product in group_products:
                    product_stable_id = extract_stable_id(product.url, product.platform)
                    if not product_stable_id:
                        print(f"[PriceTracker] ⚠️  Could not extract stable ID for {product.name[:40]}, skipping")
                        continue

                    match = next(
                        (r for r in results
                         if extract_stable_id(r.url, product.platform) == product_stable_id),
                        None
                    )

                    if match:
                        record = PriceRecord(
                            product_id = product.id,
                            price      = match.price,
                            scraped_at = datetime.now(timezone.utc),
                        )
                        db.add(record)
                        print(f"[PriceTracker] ✅ {platform} | {product.name[:40]} | ₹{match.price}")
                    else:
                        print(f"[PriceTracker] ⚠️  No ID match for {product.name[:40]} "
                              f"(product may have dropped out of top results)")

            except Exception as e:
                print(f"[PriceTracker] ❌ Error scraping '{query}' on {platform}: {e}")

        db.commit()
        print(f"[PriceTracker] Done — price history updated")

    finally:
        db.close()