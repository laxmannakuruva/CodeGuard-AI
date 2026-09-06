import { useEffect, useState } from "react";
import Stepper from "./components/Stepper";
import UploadZone from "./components/UploadZone";
import FindingsList from "./components/FindingsList";
import FixPanel from "./components/FixPanel";
import Report from "./components/Report";
import { api } from "./api";
import "./App.css";

export default function App() {
  const [health, setHealth] = useState(null);
  const [stage, setStage] = useState("upload"); // upload | findings | report
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);

  const [workspaceId, setWorkspaceId] = useState(null);
  const [findings, setFindings] = useState([]);
  const [aiAnalyzed, setAiAnalyzed] = useState(false);
  const [aiAnalyzing, setAiAnalyzing] = useState(false);
  const [aiError, setAiError] = useState(null);

  const [selectedFinding, setSelectedFinding] = useState(null);
  const [reportData, setReportData] = useState(null);
  const [hasVerifiedFixes, setHasVerifiedFixes] = useState(false);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ status: "unreachable" }));
  }, []);

  async function handleUpload(file, err) {
    if (err) {
      setUploadError(err);
      return;
    }
    setUploading(true);
    setUploadError(null);
    try {
      const data = await api.analyze(file);
      setWorkspaceId(data.workspace_id);
      setFindings(data.findings);
      setAiAnalyzed(false);
      setHasVerifiedFixes(false);
      setStage("findings");
    } catch (e) {
      setUploadError(e.message);
    } finally {
      setUploading(false);
    }
  }

  async function handleRunAiAnalysis() {
    setAiAnalyzing(true);
    setAiError(null);
    try {
      const data = await api.analyzeProject(workspaceId);
      setFindings(data.findings);
      setAiAnalyzed(true);
    } catch (e) {
      setAiError(e.message);
    } finally {
      setAiAnalyzing(false);
    }
  }

  function handleFixResolved(findingId, status) {
    setFindings((prev) => prev.map((f) => (f.id === findingId ? { ...f, status } : f)));
    if (status === "fix_verified") setHasVerifiedFixes(true);
  }

  async function handleGoToReport() {
    const data = await api.report(workspaceId);
    setReportData(data);
    setStage("report");
  }

  function handleBackToFindings() {
    setStage("findings");
  }

  function handleStartOver() {
    setStage("upload");
    setWorkspaceId(null);
    setFindings([]);
    setAiAnalyzed(false);
    setHasVerifiedFixes(false);
    setReportData(null);
    setUploadError(null);
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header-inner">
          <div className="brand">
            <span className="brand-mark">◆</span>
            <span className="brand-name">CodeGuard AI</span>
          </div>
          <div className="header-right">
            {health && (
              <div className="capability-pills">
                <span className={`pill ${health.ai_available ? "pill-on" : "pill-off"}`}>
                  AI {health.ai_available ? "on" : "off"}
                </span>
                <span className={`pill ${health.docker_available ? "pill-on" : "pill-off"}`}>
                  Docker {health.docker_available ? "on" : "off"}
                </span>
              </div>
            )}
            {workspaceId && (
              <button className="btn btn-ghost btn-sm" onClick={handleStartOver}>
                New scan
              </button>
            )}
          </div>
        </div>
      </header>

      <Stepper current={stage} />

      <main className="app-main">
        {stage === "upload" && (
          <UploadZone onUpload={handleUpload} uploading={uploading} error={uploadError} />
        )}

        {stage === "findings" && (
          <FindingsList
            findings={findings}
            aiAvailable={health?.ai_available}
            aiAnalyzed={aiAnalyzed}
            onRunAiAnalysis={handleRunAiAnalysis}
            aiAnalyzing={aiAnalyzing}
            aiError={aiError}
            onSelectFinding={setSelectedFinding}
            onGoToReport={handleGoToReport}
            hasVerifiedFixes={hasVerifiedFixes}
          />
        )}

        {stage === "report" && (
          <Report report={reportData} workspaceId={workspaceId} onBackToFindings={handleBackToFindings} />
        )}
      </main>

      {selectedFinding && (
        <FixPanel
          workspaceId={workspaceId}
          finding={selectedFinding}
          onClose={() => setSelectedFinding(null)}
          onFixResolved={handleFixResolved}
        />
      )}
    </div>
  );
}
