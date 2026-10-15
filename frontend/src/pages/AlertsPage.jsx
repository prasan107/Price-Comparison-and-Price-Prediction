import { useState } from "react";
import { getAlerts, deleteAlert } from "../utils/api";

export default function AlertsPage() {
  const [email,   setEmail]   = useState("");
  const [alerts,  setAlerts]  = useState([]);
  const [loading, setLoading] = useState(false);

  async function handleLoad(e) {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await getAlerts(email);
      setAlerts(res.data);
    } catch {
      setAlerts([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(alertId) {
    await deleteAlert(alertId);
    setAlerts(prev => prev.filter(a => a.alert_id !== alertId));
  }

  return (
    <div className="max-w-xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">My Price Alerts</h1>

      <form onSubmit={handleLoad} className="flex gap-2 mb-6">
        <input
          type="email"
          placeholder="Enter your email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          required
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="submit"
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          {loading ? "Loading…" : "Load"}
        </button>
      </form>

      {alerts.length === 0 && !loading && email && (
        <p className="text-gray-400 text-sm text-center">No active alerts for this email.</p>
      )}

      <div className="flex flex-col gap-3">
        {alerts.map(a => (
          <div key={a.alert_id} className="bg-white border border-gray-200 rounded-xl p-4 flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-700">Product #{a.product_id}</p>
              <p className="text-xs text-gray-400">
                Target: <span className="font-semibold text-gray-700">₹{a.target_price?.toLocaleString("en-IN")}</span>
                {" · "}Set {new Date(a.created_at).toLocaleDateString("en-IN")}
              </p>
            </div>
            <button
              onClick={() => handleDelete(a.alert_id)}
              className="text-xs text-red-500 hover:text-red-700 border border-red-200 px-2 py-1 rounded-lg hover:bg-red-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
