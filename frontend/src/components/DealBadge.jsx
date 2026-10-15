const CONFIG = {
  Excellent: {
    bg: "bg-green-100",
    text: "text-green-700",
    border: "border-green-300",
    emoji: "🔥",
  },

  Good: {
    bg: "bg-blue-100",
    text: "text-blue-700",
    border: "border-blue-300",
    emoji: "👍",
  },

  Wait: {
    bg: "bg-yellow-100",
    text: "text-yellow-700",
    border: "border-yellow-300",
    emoji: "⏳",
  },
};

export default function DealBadge({
  verdict,
  score,
  reasons = [],
}) {
  const c = CONFIG[verdict] || CONFIG.Wait;

  return (
    <div
      className={`inline-flex flex-col gap-1 px-3 py-2 rounded-lg border ${c.bg} ${c.border}`}
    >
      <span
        className={`text-sm font-semibold ${c.text}`}
      >
        {c.emoji} {verdict || "Deal"} · {score ?? 0}/100
      </span>

      {reasons.length > 0 && (
        <ul
          className={`text-xs ${c.text} list-disc list-inside`}
        >
          {reasons.slice(0, 2).map((reason, index) => (
            <li key={index}>
              {reason}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}