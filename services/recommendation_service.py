from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session
from db.models import Product
import numpy as np


def get_similar_products(
    product_id: int,
    db: Session,
    top_n: int = 5,
    same_platform_only: bool = False,
) -> list[dict]:
    """
    TF-IDF cosine similarity on product names.
    Finds the top_n most similar products to the given product_id.

    Why TF-IDF here:
    - Product names like "Samsung Galaxy M34 5G 128GB Blue" share meaningful
      tokens (brand, model, storage, colour) with similar products.
    - TF-IDF weights rare tokens (model number) higher than common ones (5G, blue).
    - No embedding model needed — fast, explainable, already on your resume.
    """
    query = db.query(Product)
    if same_platform_only:
        source = db.query(Product).filter(Product.id == product_id).first()
        if source:
            query = query.filter(Product.platform == source.platform)

    all_products = query.all()
    if len(all_products) < 2:
        return []

    names   = [p.name for p in all_products]
    ids     = [p.id   for p in all_products]

    # Build TF-IDF matrix
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
    try:
        tfidf_matrix = vectorizer.fit_transform(names)
    except ValueError:
        return []

    # Find target product index
    try:
        target_idx = ids.index(product_id)
    except ValueError:
        return []

    # Cosine similarity between target and all others
    target_vec   = tfidf_matrix[target_idx]
    similarities = cosine_similarity(target_vec, tfidf_matrix).flatten()

    # Get top_n most similar (exclude self)
    similar_indices = np.argsort(similarities)[::-1]
    similar_indices = [i for i in similar_indices if i != target_idx][:top_n]

    results = []
    for idx in similar_indices:
        p = all_products[idx]
        results.append({
            "product_id":  p.id,
            "name":        p.name,
            "platform":    p.platform,
            "url":         p.url,
            "image_url":   p.image_url,
            "similarity":  round(float(similarities[idx]), 3),
        })

    return results
