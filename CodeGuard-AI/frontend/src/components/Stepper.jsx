import "./Stepper.css";

const STAGES = [
  { key: "upload", label: "Upload" },
  { key: "findings", label: "Findings" },
  { key: "fix", label: "Fix & verify" },
  { key: "report", label: "Report" },
];

export default function Stepper({ current }) {
  const currentIndex = STAGES.findIndex((s) => s.key === current);

  return (
    <div className="stepper" role="list" aria-label="Pipeline progress">
      {STAGES.map((stage, i) => {
        const state = i < currentIndex ? "done" : i === currentIndex ? "active" : "pending";
        return (
          <div className="stepper-item" data-state={state} key={stage.key} role="listitem">
            <div className="stepper-dot">{state === "done" ? "✓" : i + 1}</div>
            <div className="stepper-label">{stage.label}</div>
            {i < STAGES.length - 1 && <div className="stepper-line" data-state={state} />}
          </div>
        );
      })}
    </div>
  );
}
