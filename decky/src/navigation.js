const parent = {
  results:"search", system:"results", destination:"system", confirm:"destination",
  jobs:"search", library:"search", game:"library", report:"game", checks:"library"
};
export function previous(screen) { return parent[screen] ?? "search"; }
export function jobAction(state) {
  if (["queued","resolving","downloading","verifying"].includes(state)) return "cancel";
  if (["needs_attention","failed","cancelled"].includes(state)) return "retry";
  return null;
}

