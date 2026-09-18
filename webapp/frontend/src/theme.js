// Mirrors app/theme.py's TIER_COLOR + colour roles, so severity tiers read identically
// between the Streamlit app and this frontend.
export const COLORS = {
  green: 'var(--gx-green)',
  amber: 'var(--gx-amber)',
  red: 'var(--gx-red)',
  dim: 'var(--gx-dim)',
  faint: 'var(--gx-faint)',
  accent: 'var(--gx-accent)',
  body: 'var(--gx-body)',
  text: 'var(--gx-text)',
};

export const TIER_COLOR = { ok: 'green', monitor: 'amber', inspect: 'amber', act: 'red', unknown: 'dim' };

export function tierColor(tier) {
  return COLORS[TIER_COLOR[tier] ?? 'dim'];
}
