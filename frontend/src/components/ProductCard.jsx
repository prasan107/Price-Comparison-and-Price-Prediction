import { useNavigate } from "react-router-dom";

const PLATFORM_COLORS = {
  amazon:   { bg: "bg-orange-50",  border: "border-orange-200", label: "bg-orange-500" },
  flipkart: { bg: "bg-blue-50",    border: "border-blue-200",   label: "bg-blue-600"   },
};

// Filter out Flipkart rating strings like "4.657,795 Ratings & 3,732 Reviews"
// and any description that is just a number/rating pattern
function cleanDescription(desc) {
  if (!desc) return "";
  // Remove segments that look like "4.5 | 12,345 Ratings" or "57,795 Ratings & 3,732 Reviews"
  const cleaned = desc
    .replace(/\d+\.\d+\s*\|?\s*[\d,]+\s*(Ratings?|Reviews?)[^|]*/gi, "")
    .replace(/[\d,]+\s*(Ratings?|Reviews?)\s*(&\s*[\d,]+\s*(Ratings?|Reviews?))?/gi, "")
    .replace(/\|\s*\|/g, "|")   // clean up double pipes left behind
    .replace(/^\s*\|\s*/, "")   // trim leading pipe
    .replace(/\s*\|\s*$/, "")   // trim trailing pipe
    .trim();
  return cleaned;
}

export default function ProductCard({ product, isBestValue = false }) {
  const navigate = useNavigate();
  const c = PLATFORM_COLORS[product.platform] || PLATFORM_COLORS.amazon;
  const hasValidUrl = product.url && product.url !== "N/A";
  const desc = cleanDescription(product.description);

  function goToDetail(e) {
    if (e.target.closest("a") || e.target.closest("button")) return;
    navigate(`/product/${product.product_id}`);
  }

  return (
    <div
      onClick={goToDetail}
      className={`relative rounded-xl border ${c.border} ${c.bg} p-4 flex gap-4
                  hover:shadow-md transition-shadow cursor-pointer`}
    >
      {/* Best Value ribbon */}
      {isBestValue && (
        <div className="absolute -top-2 -left-2 bg-green-500 text-white
                        text-xs font-bold px-2 py-0.5 rounded-full shadow">
          ★ Best Value
        </div>
      )}

      {/* Product image */}
      <img
        src={product.image_url}
        alt={product.name}
        className="w-20 h-20 object-contain rounded-lg bg-white
                   border border-gray-100 flex-shrink-0 self-start mt-1"
        onError={e => { e.target.src = "https://via.placeholder.com/80"; }}
      />

      <div className="flex-1 min-w-0">

        {/* Platform badge */}
        <span className={`inline-block text-white text-xs font-semibold
                          px-2 py-0.5 rounded ${c.label} mb-1 capitalize`}>
          {product.platform}
        </span>

        {/* Product name */}
        <p className="text-sm font-semibold text-gray-800 line-clamp-2 mb-1 leading-snug">
          {product.name}
        </p>

        {/* Description — 2 lines so spec bullets are readable */}
        {desc && (
          <p className="text-xs text-gray-500 line-clamp-2 mb-2">
            {desc}
          </p>
        )}

        {/* Click hint */}
        <p className="text-xs text-blue-400 mb-2">
          Click card for price history &amp; forecast →
        </p>

        {/* Price row */}
        <div className="flex items-center gap-3 flex-wrap mb-3">
          <span className="text-2xl font-bold text-gray-900">
            ₹{product.current_price?.toLocaleString("en-IN")}
          </span>

          {product.min_price && product.current_price > product.min_price && (
            <span className="text-xs text-gray-400">
              All-time low: ₹{product.min_price.toLocaleString("en-IN")}
            </span>
          )}

          {product.pct_vs_avg != null && (
            <span className={`text-xs font-medium
                              ${product.pct_vs_avg <= 0 ? "text-green-600" : "text-red-500"}`}>
              {product.pct_vs_avg <= 0 ? "▼" : "▲"} {Math.abs(product.pct_vs_avg)}% vs avg
            </span>
          )}
        </div>

        {/* Buttons */}
        <div className="flex gap-2 flex-wrap">
          {hasValidUrl ? (
            <a
              href={product.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs bg-gray-900 text-white px-3 py-1.5 rounded-lg
                         hover:bg-gray-700 transition-colors"
            >
              Buy on {product.platform === "amazon" ? "Amazon" : "Flipkart"} →
            </a>
          ) : (
            <span className="text-xs bg-gray-200 text-gray-400 px-3 py-1.5
                             rounded-lg cursor-not-allowed">
              URL unavailable
            </span>
          )}
          <button
            onClick={() => navigate(`/product/${product.product_id}`)}
            className="text-xs bg-white border border-gray-300 text-gray-700
                       px-3 py-1.5 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Price history →
          </button>
        </div>
      </div>
    </div>
  );
}