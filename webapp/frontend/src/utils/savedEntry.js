// Single source of truth for what a saved snapshot looks like, so the Save button next to a
// page's "accepted" banner and the one in its bottom action row always agree on the same id.
export function buildSavedEntry(subsystem, result) {
  return {
    id: `${subsystem}:${result.file_id}`,
    subsystem,
    fileId: result.file_id,
    headline: result.headline,
    tier: result.tier,
    tierLabel: result.tier_label,
    result,
  };
}
