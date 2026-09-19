// The door dataset stamps rows as 'Y-M-D-h-m-s-ms' with no zero padding (2023-7-5-0-0-15-5 is
// 15.005 s, not 15.5 s) — mirrors subsystems/door/loader.py::parse_ts. The CSV keeps that raw
// form because it's what gets scored; this is only for showing it to a person.

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const pad = (v, n = 2) => String(v).padStart(n, '0');

// Returns epoch ms in UTC (no local-timezone shift — the stamps carry no zone), or null.
export function parseDoorTs(s) {
  if (s == null) return null;
  const parts = String(s).split('-');
  if (parts.length === 7 && parts.every((p) => /^\d+$/.test(p))) {
    const [y, mo, d, h, mi, sec, ms] = parts.map(Number);
    return Date.UTC(y, mo - 1, d, h, mi, sec, ms);
  }
  const t = Date.parse(s);
  return Number.isNaN(t) ? null : t;
}

export const formatDate = (t) => {
  const d = new Date(t);
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
};

export const formatClock = (t) => {
  const d = new Date(t);
  return `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}.${pad(d.getUTCMilliseconds(), 3)}`;
};

// 3.76 s · 1 min 05 s · 2 h 04 min
export function formatDuration(ms) {
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(2)} s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m} min ${pad(Math.floor(s % 60))} s`;
  return `${Math.floor(m / 60)} h ${pad(m % 60)} min`;
}
