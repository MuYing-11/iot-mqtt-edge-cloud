export const last = (arr) => (arr && arr.length ? arr[arr.length - 1] : null);

export function fmtBytes(b) {
  if (b == null) return "–";
  if (b < 1024) return `${Math.round(b)} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1024 / 1024).toFixed(2)} MB`;
}

export function fmtDuration(s) {
  if (s == null) return "–";
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return h ? `${h}h ${m}m` : `${m}m ${Math.floor(s % 60)}s`;
}

export const fmtTime = (ts) => new Date(ts * 1000).toLocaleTimeString();

export function avg(arr, key, n = 30) {
  const slice = arr.slice(-n);
  if (!slice.length) return 0;
  return slice.reduce((s, x) => s + (x[key] || 0), 0) / slice.length;
}

// insert a null point where data is missing for more than maxGapMs, so lines break instead of
// drawing a straight segment over the gap
export function gapped(points, maxGapMs = 10000) {
  const out = [];
  for (let i = 0; i < points.length; i++) {
    if (i && points[i][0] - points[i - 1][0] > maxGapMs) out.push([points[i - 1][0] + 1, null]);
    out.push(points[i]);
  }
  return out;
}
