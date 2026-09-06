import "./DiffView.css";

/** Parses a unified diff string into renderable line objects. */
function parseDiff(diffText) {
  if (!diffText) return [];
  return diffText.split("\n").map((line) => {
    if (line.startsWith("+++") || line.startsWith("---")) return { type: "header", text: line };
    if (line.startsWith("@@")) return { type: "hunk", text: line };
    if (line.startsWith("+")) return { type: "add", text: line.slice(1) };
    if (line.startsWith("-")) return { type: "remove", text: line.slice(1) };
    return { type: "context", text: line.startsWith(" ") ? line.slice(1) : line };
  });
}

export default function DiffView({ diff }) {
  const lines = parseDiff(diff);

  if (lines.length === 0) {
    return <div className="diff-empty">No textual diff available.</div>;
  }

  return (
    <div className="diff-view mono">
      {lines.map((line, i) => (
        <div className={`diff-line diff-${line.type}`} key={i}>
          <span className="diff-marker">
            {line.type === "add" ? "+" : line.type === "remove" ? "−" : ""}
          </span>
          <span className="diff-text">{line.text || " "}</span>
        </div>
      ))}
    </div>
  );
}
