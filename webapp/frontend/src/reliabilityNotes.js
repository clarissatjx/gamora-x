// Short, plain-language reliability notes for the hover next to each verdict — deliberately not
// the full sourced text from app/reliability.py (recall/precision, cross-validation methodology,
// PLAN.md citations). That detail matters for the official submission app; here the audience is
// an operator who just wants "can I trust this," in one sentence, no ML vocabulary required.
export const RELIABILITY_NOTE = {
  door: 'Checked against real door recordings — it catches abnormal cycles reliably, though a borderline case could still slip through.',
  acv: 'Checked against every case we have an answer for — it named the right car every time, on a small number of cases.',
  rail: "Checked against recordings it hadn't seen before — right most of the time, but light corrugation can still be missed.",
  shm: 'Checked against real segments — typically accurate to a few percent, occasionally more off on an unusual one.',
};
