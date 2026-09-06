import Badge from "./Badge";
import "./FindingsList.css";

const SEVERITY_ORDER = { high: 0, medium: 1, low: 2 };

export default function FindingsList({
  findings,
  aiAvailable,
  aiAnalyzed,
  onRunAiAnalysis,
  aiAnalyzing,
  aiError,
  onSelectFinding,
  onGoToReport,
  hasVerifiedFixes,
}) {
  const sorted = [...findings].sort((a, b) => {
    const sevDiff = SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity];
    if (sevDiff !== 0) return sevDiff;
    return a.file.localeCompare(b.file);
  });

  const counts = findings.reduce(
    (acc, f) => {
      acc.total += 1;
      acc[f.severity] = (acc[f.severity] || 0) + 1;
      return acc;
    },
    { total: 0, high: 0, medium: 0, low: 0 }
  );

  return (
    <div className="findings-screen">
      <div className="findings-summary">
        <div className="summary-stats">
          <div className="stat">
            <span className="stat-value">{counts.total}</span>
            <span className="stat-label">findings</span>
          </div>
          <div className="stat stat-high">
            <span className="stat-value">{counts.high || 0}</span>
            <span className="stat-label">high</span>
          </div>
          <div className="stat stat-medium">
            <span className="stat-value">{counts.medium || 0}</span>
            <span className="stat-label">medium</span>
          </div>
          <div className="stat stat-low">
            <span className="stat-value">{counts.low || 0}</span>
            <span className="stat-label">low</span>
          </div>
        </div>

        <div className="summary-actions">
          {!aiAnalyzed && (
            <button
              className="btn btn-accent"
              onClick={onRunAiAnalysis}
              disabled={!aiAvailable || aiAnalyzing}
              title={!aiAvailable ? "Set ANTHROPIC_API_KEY on the server to enable AI analysis" : undefined}
            >
              {aiAnalyzing ? "Analyzing with AI…" : "Run AI analysis"}
            </button>
          )}
          {hasVerifiedFixes && (
            <button className="btn btn-ghost" onClick={onGoToReport}>
              View report →
            </button>
          )}
        </div>
      </div>

      {!aiAvailable && !aiAnalyzed && (
        <div className="notice notice-info">
          AI analysis and AI fix generation are unavailable — no <code>ANTHROPIC_API_KEY</code> is
          configured on the server. Static and security analysis above are fully functional without it.
        </div>
      )}
      {aiError && <div className="notice notice-error">{aiError}</div>}

      <div className="findings-list">
        {sorted.length === 0 && (
          <div className="empty-state">No findings — nice and clean.</div>
        )}
        {sorted.map((f) => (
          <button className="finding-card" key={f.id} onClick={() => onSelectFinding(f)}>
            <div className="finding-card-top">
              <Badge kind={f.severity}>{f.severity}</Badge>
              <Badge kind={f.source}>{f.source}</Badge>
              {f.status !== "open" && <Badge kind={f.status}>{f.status.replace("_", " ")}</Badge>}
              <span className="finding-tool">{f.tool}</span>
            </div>
            <div className="finding-desc">{f.description}</div>
            <div className="finding-loc mono">
              {f.file}{f.line ? `:${f.line}` : ""}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
