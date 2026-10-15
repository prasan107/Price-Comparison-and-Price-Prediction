from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from db.database import get_db
from services.scraper_service import run_all_scrapers, save_to_db
from services.comparison_service import build_comparison_result
from services.recommendation_service import get_similar_products

router = APIRouter()


class SearchRequest(BaseModel):
    query: str


@router.post("/search")
async def search(request: SearchRequest, db: Session = Depends(get_db)):
    """
    Main search endpoint.
    1. Runs Amazon + Flipkart scrapers in parallel
    2. Saves all results + price records to PostgreSQL
    3. Returns ranked comparison + best value pick
    """
    query = request.query.strip()
    if not query:
        return {"error": "Search query cannot be empty"}

    # Step 1: Parallel scrape
    scraped = await run_all_scrapers(query)
    if not scraped:
        return {"error": "No results found. Try a different search term."}

    # Step 2: Save to DB (builds price history)
    saved_products = save_to_db(scraped, db)

    # Step 3: Build comparison
    comparison = build_comparison_result(saved_products, db)

    return {
        "query":      query,
        "total":      len(comparison["products"]),
        "comparison": comparison,
    }


@router.get("/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a single product with similar product recommendations."""
    from db.models import Product
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return {"error": "Product not found"}

    similar = get_similar_products(product_id, db, top_n=5)

    return {
        "product": {
            "id":          product.id,
            "name":        product.name,
            "platform":    product.platform,
            "url":         product.url,
            "image_url":   product.image_url,
            "description": product.description,
        },
        "similar_products": similar,
    }
