export default function DataTable({ headers, rows, title, schema, footer }) {
  return (
    <div className="gx-table-wrap">
      <div className="gx-table-head">
        <div className="gx-panel-h">{title}</div>
        <div className="mono" style={{ fontSize: 12, color: 'var(--gx-faint)' }}>{schema}</div>
      </div>
      <div className="gx-table-scroll">
        <table className="gx">
          <thead><tr>{headers.map((h) => <th key={h}>{h}</th>)}</tr></thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>{r.map((c, j) => <td key={j}>{c}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
      {footer && <div className="gx-foot">{footer}</div>}
    </div>
  );
}
