export default function Panel({ heading, sub, right, children }) {
  return (
    <div className="gx-panel">
      {heading !== undefined && (
        <div className="gx-panel-head">
          <div className="gx-panel-h">{heading}</div>
          {right}
        </div>
      )}
      {sub && <div className="gx-panel-s">{sub}</div>}
      {children}
    </div>
  );
}
