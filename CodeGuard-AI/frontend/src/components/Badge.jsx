import "./Badge.css";

export default function Badge({ kind, children }) {
  return (
    <span className={`badge badge-${kind}`}>
      {children}
    </span>
  );
}
