import Badge from "./Badge";
import { api } from "../api";
import "./Report.css";

export default function Report({ report, workspaceId, onBackToFindings }) {
  if (!report) return null;

  const { total_findings, by_severity, by_status, by_source, files_analyzed, fixes_verified, fixes_failed } = report;

  return (
    <div className="report-screen">
      <div className="report-header">
        <h2 className="report-title">Scan report</h2>
        <div className="report-header-actions">
          <button className="btn btn-ghost" onClick={onBackToFindings}>← Back to findings</button>
          <a className="btn btn-accent" href={api.downloadUrl(workspaceId)} download>
            Download fixed project
          </a>
        </div>
      </div>

      <div className="report-grid">
        <div className="report-card">
          <div className="report-card-value">{files_analyzed}</div>
          <div className="report-card-label">Python files analyzed</div>
        </div>
        <div className="report-card">
          <div className="report-card-value">{total_findings}</div>
          <div className="report-card-label">Total findings</div>
        </div>
        <div className="report-card report-card-success">
          <div className="report-card-value">{fixes_verified}</div>
          <div className="report-card-label">Fixes verified</div>
        </div>
        <div className="report-card report-card-danger">
          <div className="report-card-value">{fixes_failed}</div>
          <div className="report-card-label">Fixes failed</div>
        </div>
      </div>

      <div className="report-breakdown">
        <div className="breakdown-block">
          <h3 className="breakdown-title">By severity</h3>
          {Object.entries(by_severity).length === 0 && <p className="breakdown-empty">—</p>}
          {Object.entries(by_severity).map(([sev, count]) => (
            <div className="breakdown-row" key={sev}>
              <Badge kind={sev}>{sev}</Badge>
              <span className="breakdown-count mono">{count}</span>
            </div>
          ))}
        </div>

        <div className="breakdown-block">
          <h3 className="breakdown-title">By source</h3>
          {Object.entries(by_source).length === 0 && <p className="breakdown-empty">—</p>}
          {Object.entries(by_source).map(([src, count]) => (
            <div className="breakdown-row" key={src}>
              <Badge kind={src}>{src}</Badge>
              <span className="breakdown-count mono">{count}</span>
            </div>
          ))}
        </div>

        <div className="breakdown-block">
          <h3 className="breakdown-title">By status</h3>
          {Object.entries(by_status).length === 0 && <p className="breakdown-empty">—</p>}
          {Object.entries(by_status).map(([status, count]) => (
            <div className="breakdown-row" key={status}>
              <Badge kind={status}>{status.replace(/_/g, " ")}</Badge>
              <span className="breakdown-count mono">{count}</span>
            </div>
          ))}
        </div>
      </div>

      <p className="report-footnote">
        All figures above are computed directly from this scan's findings and fix attempts —
        nothing here is simulated.
      </p>
    </div>
  );
}
