import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";

import {
  getPriceHistory,
  getPrediction,
  getProduct,
  createAlert,
} from "../utils/api";

import PriceChart from "../components/PriceChart";
import DealBadge from "../components/DealBadge";

const PLATFORM_COLORS = {
  amazon: {
    label: "bg-orange-500",
    text: "Amazon",
  },

  flipkart: {
    label: "bg-blue-600",
    text: "Flipkart",
  },
};

// Strip Flipkart rating lines such as:
// "4.6 | 57,795 Ratings & 3,732 Reviews"
function cleanDescription(desc) {
  if (!desc) return "";

  return desc
    .replace(
      /\d+\.\d+\s*\|?\s*[\d,]+\s*(Ratings?|Reviews?)[^|]*/gi,
      ""
    )
    .replace(
      /[\d,]+\s*(Ratings?|Reviews?)\s*(&\s*[\d,]+\s*(Ratings?|Reviews?))?/gi,
      ""
    )
    .replace(/\|\s*\|/g, "|")
    .replace(/^\s*\|\s*/, "")
    .replace(/\s*\|\s*$/, "")
    .trim();
}

export default function ProductPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [product, setProduct] = useState(null);
  const [similar, setSimilar] = useState([]);
  const [history, setHistory] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(true);

  const [alertEmail, setAlertEmail] = useState("");
  const [alertTarget, setAlertTarget] = useState("");
  const [alertMsg, setAlertMsg] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const [prodRes, histRes, predRes] = await Promise.all([
          getProduct(id),
          getPriceHistory(id),
          getPrediction(id),
        ]);

        setProduct(prodRes.data.product);
        setSimilar(prodRes.data.similar_products || []);
        setHistory(histRes.data.data || []);
        setPrediction(predRes.data);
      } catch (error) {
        console.error("Failed to load product page:", error);
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [id]);

  async function handleAlert(event) {
    event.preventDefault();

    try {
      await createAlert({
        product_id: parseInt(id),
        target_price: parseFloat(alertTarget),
        email: alertEmail,
      });

      setAlertMsg(
        "Alert set! We'll email you when the price drops."
      );
    } catch (error) {
      console.error("Failed to create alert:", error);

      setAlertMsg(
        "Could not create the alert. Please try again."
      );
    }
  }

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-10">
        <div className="text-center text-gray-500">
          Loading product...
        </div>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-10">
        <div className="bg-white border border-gray-200 rounded-xl p-6 text-center">
          <h2 className="text-lg font-semibold text-gray-800">
            Product not found
          </h2>

          <button
            onClick={() => navigate("/")}
            className="mt-4 bg-blue-600 text-white px-4 py-2 rounded-lg"
          >
            Back to search
          </button>
        </div>
      </div>
    );
  }

  const forecast = prediction?.forecast?.forecast || [];
  const deal = prediction?.deal;
  const fc = prediction?.forecast;

  const platform =
    PLATFORM_COLORS[product.platform?.toLowerCase()] || {
      label: "bg-gray-500",
      text: product.platform || "Unknown",
    };

  const description = cleanDescription(product.description);

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">

      {/* Back */}
      <button
        onClick={() => navigate(-1)}
        className="text-sm text-blue-600 hover:text-blue-800 mb-4"
      >
        ← Back
      </button>

      {/* Product information */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 mb-6">
        <div className="flex flex-col md:flex-row gap-6">

          {/* Product image */}
          <div className="md:w-1/3 flex items-center justify-center">
            {product.image_url ? (
              <img
                src={product.image_url}
                alt={product.name}
                className="max-h-72 max-w-full object-contain rounded-lg"
              />
            ) : (
              <div className="h-64 w-full bg-gray-100 rounded-lg flex items-center justify-center text-gray-400">
                No image
              </div>
            )}
          </div>

          {/* Product details */}
          <div className="flex-1">

            <div className="flex items-center gap-2 mb-2">
              <span
                className={`text-xs text-white px-2 py-1 rounded ${platform.label}`}
              >
                {platform.text}
              </span>
            </div>

            <h1 className="text-xl font-semibold text-gray-900 mb-3">
              {product.name}
            </h1>

            {description && (
              <p className="text-sm text-gray-600 mb-4">
                {description}
              </p>
            )}

            {product.url && (
              <a
                href={product.url}
                target="_blank"
                rel="noreferrer"
                className="inline-block text-sm text-blue-600 hover:underline"
              >
                View product →
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Deal score */}
      {deal && (
        <div className="mb-6">
          <DealBadge
            verdict={deal.verdict}
            score={deal.score}
            reasons={deal.reasons}
          />
        </div>
      )}

      {/* Forecast cards */}
      {fc && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">

          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <p className="text-xs text-gray-400 mb-1">
              Current price
            </p>

            <p className="text-xl font-semibold text-gray-900">
              ₹{fc.current_price?.toLocaleString("en-IN")}
            </p>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <p className="text-xs text-gray-400 mb-1">
              7-day forecast
            </p>

            <p className="text-xl font-semibold text-gray-900">
              ₹{fc.predicted_price?.toLocaleString("en-IN")}
            </p>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <p className="text-xs text-gray-400 mb-1">
              History points
            </p>

            <p className="text-xl font-semibold text-gray-900">
              {history.length}
            </p>
          </div>

        </div>
      )}

      {/* History warning */}
      {history.length < 5 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 mb-6">
          <p className="text-sm text-yellow-800">
            Only {history.length} price point
            {history.length !== 1 ? "s" : ""} recorded.
            Search this product a few more times to build history
            for forecasting.
          </p>
        </div>
      )}

      {/* Price chart */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 mb-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">
          Price history + 7-day forecast
        </h2>

        <PriceChart
          history={history}
          forecast={forecast}
        />

        <p className="text-xs text-gray-400 mt-2">
          Blue = actual · Green dashed = forecast · Light green = 95% confidence band
        </p>
      </div>

      {/* Similar products */}
      {similar.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-5 mb-6">

          <h2 className="text-sm font-semibold text-gray-700 mb-3">
            Similar products
          </h2>

          <div className="flex flex-col gap-2">
            {similar.map((item) => (
              <div
                key={item.product_id}
                onClick={() =>
                  navigate(`/product/${item.product_id}`)
                }
                className="flex items-center justify-between p-3 border border-gray-100 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
              >

                <div className="flex-1 min-w-0">

                  <p className="text-xs font-medium text-gray-800 line-clamp-1">
                    {item.name}
                  </p>

                  <p className="text-xs text-gray-400 capitalize">
                    {item.platform}
                  </p>

                </div>

                <span className="text-xs text-blue-500 ml-2 flex-shrink-0">
                  View →
                </span>

              </div>
            ))}
          </div>
        </div>
      )}

      {/* Price alert */}
      <div className="bg-white border border-gray-200 rounded-xl p-5">

        <h2 className="text-sm font-semibold text-gray-700 mb-4">
          🔔 Set a price drop alert
        </h2>

        <form
          onSubmit={handleAlert}
          className="flex flex-col gap-3"
        >

          <input
            type="email"
            placeholder="Your email"
            value={alertEmail}
            onChange={(event) =>
              setAlertEmail(event.target.value)
            }
            required
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />

          <input
            type="number"
            placeholder={
              fc
                ? `Target price (current: ₹${fc.current_price?.toLocaleString(
                    "en-IN"
                  )})`
                : "Target price (₹)"
            }
            value={alertTarget}
            onChange={(event) =>
              setAlertTarget(event.target.value)
            }
            required
            min="1"
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />

          <button
            type="submit"
            className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            Set Alert
          </button>

        </form>

        {alertMsg && (
          <p className="text-sm mt-3 text-gray-600">
            {alertMsg}
          </p>
        )}

      </div>

    </div>
  );
}