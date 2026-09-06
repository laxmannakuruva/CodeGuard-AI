import { useState } from "react";
import Badge from "./Badge";
import DiffView from "./DiffView";
import { api } from "../api";
import "./FixPanel.css";

export default function FixPanel({ workspaceId, finding, onClose, onFixResolved }) {
  const [proposal, setProposal] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState(null);

  const [applying, setApplying] = useState(false);
  const [result, setResult] = useState(null);
  const [applyError, setApplyError] = useState(null);

  async function handleGenerate() {
    setGenerating(true);
    setGenError(null);
    try {
      const data = await api.generateFix(workspaceId, finding.id);
      setProposal(data);
    } catch (e) {
      setGenError(e.message);
    } finally {
      setGenerating(false);
    }
  }

  async function handleApprove() {
    setApplying(true);
    setApplyError(null);
    try {
      const data = await api.applyFix(workspaceId, finding.id);
      setResult(data);
      onFixResolved(finding.id, data.status);
    } catch (e) {
      setApplyError(e.message);
    } finally {
      setApplying(false);
    }
  }

  function handleReject() {
    setProposal(null);
    setResult(null);
  }

  return (
    <div className="fixpanel-overlay" onClick={onClose}>
      <div className="fixpanel" onClick={(e) => e.stopPropagation()}>
        <div className="fixpanel-header">
          <div>
            <div className="fixpanel-badges">
              <Badge kind={finding.severity}>{finding.severity}</Badge>
              <Badge kind={finding.source}>{finding.source}</Badge>
              <span className="fixpanel-tool">{finding.tool}</span>
            </div>
            <h2 className="fixpanel-title">{finding.description}</h2>
            <p className="fixpanel-loc mono">{finding.file}{finding.line ? `:${finding.line}` : ""}</p>
          </div>
          <button className="fixpanel-close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <div className="fixpanel-body">
          {!proposal && !result && (
            <div className="fixpanel-start">
              <p className="fixpanel-hint">
                Generate an AI-proposed fix for this finding. You'll see the original and fixed
                code side by side before anything is applied.
              </p>
              <button className="btn btn-accent" onClick={handleGenerate} disabled={generating}>
                {generating ? "Generating fix…" : "Generate AI fix"}
              </button>
              {genError && <div className="notice notice-error" style={{ marginTop: 14 }}>{genError}</div>}
            </div>
          )}

          {proposal && !result && (
            <>
              <div className="fixpanel-explanation">{proposal.explanation}</div>
              <div className="fixpanel-diff-label">Proposed change</div>
              <DiffView diff={proposal.diff} />

              <div className="fixpanel-approval">
                <p className="fixpanel-hint">
                  Approve to apply this fix in an isolated workspace, run the test suite in the
                  sandbox, and verify it before merging.
                </p>
                <div className="fixpanel-actions">
                  <button className="btn btn-ghost" onClick={handleReject} disabled={applying}>
                    Reject
                  </button>
                  <button className="btn btn-success" onClick={handleApprove} disabled={applying}>
                    {applying ? "Applying & testing in sandbox…" : "Approve & apply fix"}
                  </button>
                </div>
                {applyError && <div className="notice notice-error" style={{ marginTop: 14 }}>{applyError}</div>}
              </div>
            </>
          )}

          {result && (
            <div className="fixpanel-result">
              <div className={`result-banner result-${result.status}`}>
                {result.status === "fix_verified" ? "✓ Fix verified" : "✕ Fix failed verification"}
              </div>

              <div className="result-grid">
                <div className="result-row">
                  <span className="result-label">Compiles</span>
                  <span className={result.compile_check ? "result-ok" : "result-bad"}>
                    {result.compile_check ? "yes" : "no"}
                  </span>
                </div>
                <div className="result-row">
                  <span className="result-label">Tests</span>
                  <span className={result.tests_result === "passed" ? "result-ok" : result.tests_result === "no_tests_found" ? "result-neutral" : "result-bad"}>
                    {result.tests_result.replace(/_/g, " ")}
                  </span>
                </div>
                <div className="result-row">
                  <span className="result-label">Original issue</span>
                  <span className={result.static_recheck === "resolved" ? "result-ok" : result.static_recheck === "not_checked" ? "result-neutral" : "result-bad"}>
                    {result.static_recheck.replace(/_/g, " ")}
                  </span>
                </div>
                <div className="result-row">
                  <span className="result-label">Isolation</span>
                  <span className="result-neutral mono">{result.isolation_mode}</span>
                </div>
              </div>

              {result.logs && (
                <>
                  <div className="fixpanel-diff-label">Sandbox output</div>
                  <pre className="result-logs mono">{result.logs}</pre>
                </>
              )}

              <div className="fixpanel-diff-label">Applied diff</div>
              <DiffView diff={proposal.diff} />

              <div className="fixpanel-actions">
                <button className="btn btn-ghost" onClick={onClose}>Close</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
