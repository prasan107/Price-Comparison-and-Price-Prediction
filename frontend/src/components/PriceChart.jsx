import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ReferenceLine, ReferenceArea, ResponsiveContainer,
} from "recharts";

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString("en-IN", { month: "short", day: "numeric" });
}

function formatPrice(val) {
  return `₹${Number(val).toLocaleString("en-IN")}`;
}

export default function PriceChart({ history = [], forecast = [] }) {
  // Merge history + forecast into one array for the chart
  const historyData = history.map(h => ({
    date:  h.date,
    price: h.price,
    type:  "actual",
  }));

  const forecastData = forecast.map(f => ({
    date:       f.ds,
    predicted:  f.yhat,
    lower:      f.yhat_lower,
    upper:      f.yhat_upper,
    type:       "forecast",
  }));

  // Join point — last actual becomes first forecast anchor
  const joinPoint = historyData.length > 0
    ? { date: historyData.at(-1).date, predicted: historyData.at(-1).price }
    : null;

  const forecastWithJoin = joinPoint ? [joinPoint, ...forecastData] : forecastData;

  if (historyData.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-gray-400 text-sm">
        No price history yet — run a few searches first.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis
          dataKey="date"
          tickFormatter={formatDate}
          tick={{ fontSize: 11 }}
          allowDuplicatedCategory={false}
        />
        <YAxis tickFormatter={v => `₹${(v/1000).toFixed(0)}k`} tick={{ fontSize: 11 }} />
        <Tooltip
          formatter={(val, name) => [formatPrice(val), name]}
          labelFormatter={formatDate}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />

        {/* Actual price history */}
        <Line
          data={historyData}
          dataKey="price"
          name="Actual price"
          stroke="#2563EB"
          strokeWidth={2}
          dot={{ r: 3 }}
          activeDot={{ r: 5 }}
        />

        {/* Forecast line */}
        {forecastWithJoin.length > 1 && (
          <Line
            data={forecastWithJoin}
            dataKey="predicted"
            name="Forecast"
            stroke="#16A34A"
            strokeWidth={2}
            strokeDasharray="6 3"
            dot={false}
          />
        )}

        {/* Confidence band (upper) */}
        {forecastWithJoin.length > 1 && (
          <Line
            data={forecastWithJoin}
            dataKey="upper"
            name="Upper bound"
            stroke="#86EFAC"
            strokeWidth={1}
            strokeDasharray="3 3"
            dot={false}
          />
        )}

        {/* Confidence band (lower) */}
        {forecastWithJoin.length > 1 && (
          <Line
            data={forecastWithJoin}
            dataKey="lower"
            name="Lower bound"
            stroke="#86EFAC"
            strokeWidth={1}
            strokeDasharray="3 3"
            dot={false}
          />
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}
