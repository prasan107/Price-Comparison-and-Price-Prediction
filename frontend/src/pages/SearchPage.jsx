import { useState, useEffect } from "react";
import { searchProducts } from "../utils/api";
import ProductCard from "../components/ProductCard";

// Cache results in module-level variable so back navigation restores them
// (sessionStorage would work too but this is simpler and instant)
let cachedResults = null;
let cachedQuery = "";

export default function SearchPage() {
  const [query,   setQuery]   = useState(cachedQuery);
  const [results, setResults] = useState(cachedResults);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);

  // Restore cached results when navigating back
  useEffect(() => {
    if (cachedResults) {
      setResults(cachedResults);
      setQuery(cachedQuery);
    }
  }, []);

  async function handleSearch(e) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setResults(null);
    cachedResults = null;
    try {
      const res = await searchProducts(query.trim());
      setResults(res.data);
      // Cache for back navigation
      cachedResults = res.data;
      cachedQuery   = query.trim();
    } catch (err) {
      setError("Search failed — make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  }

  const comparison  = results?.comparison;
  const bestValueId = comparison?.best_value?.product_id;

  return (
    <div>
      {/* Search bar */}
      <div className="text-center mb-10">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Price Comparison Engine</h1>
        <p className="text-gray-500 mb-6">
          Compare Amazon &amp; Flipkart prices with AI-powered deal scoring
        </p>
        <form onSubmit={handleSearch} className="flex gap-2 max-w-xl mx-auto">
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search for a product (e.g. Samsung Galaxy M34)"
            className="flex-1 border border-gray-300 rounded-lg px-4 py-2.5 text-sm
                       focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-blue-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium
                       hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {loading ? "Searching…" : "Search"}
          </button>
        </form>
      </div>

      {/* Loading */}
      {loading && (
        <div className="text-center text-gray-500 text-sm animate-pulse py-10">
          Scraping Amazon &amp; Flipkart in parallel… this takes ~20–40 seconds
        </div>
      )}

      {/* Error */}
      {error && <p className="text-red-500 text-center text-sm">{error}</p>}

      {/* Results */}
      {comparison && (
        <div>
          {/* Summary bar */}
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <p className="text-sm text-gray-500">
              {results.total} results for <strong>"{results.query}"</strong>
            </p>
            {comparison.best_value && (
              <div className="text-sm text-green-700 font-medium bg-green-50
                              border border-green-200 px-3 py-1 rounded-full">
                ★ Best value: ₹{comparison.best_value.current_price?.toLocaleString("en-IN")}
                {" "}on {comparison.best_value.platform}
              </div>
            )}
          </div>

          {/* Platform cheapest summary */}
          {Object.keys(comparison.by_platform).length > 1 && (
            <div className="grid grid-cols-2 gap-3 mb-6">
              {Object.entries(comparison.by_platform).map(([platform, p]) => (
                <div key={platform}
                     className="bg-white border border-gray-200 rounded-lg p-3 text-sm">
                  <span className="font-medium capitalize">{platform}</span>
                  <span className="text-gray-500"> cheapest: </span>
                  <span className="font-bold">
                    ₹{p.current_price?.toLocaleString("en-IN")}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Product cards */}
          <div className="flex flex-col gap-3">
            {comparison.products.map(p => (
              <ProductCard
                key={p.product_id}
                product={p}
                isBestValue={p.product_id === bestValueId}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}