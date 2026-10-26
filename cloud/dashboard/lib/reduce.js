// Shared state reducer: used by the server hub (history) and by the browser (live updates).

export const SENSORS = {
  temperature: { label: "Temperature", unit: "°C", color: "#3987e5" },
  humidity: { label: "Humidity", unit: "%", color: "#d95926" },
  pressure: { label: "Pressure", unit: "hPa", color: "#199e70" },
  co2: { label: "Air quality (CO₂)", unit: "ppm", color: "#c98500" },
};

const LIMITS = { sensor: 900, stats: 600, system: 360, alerts: 50, log: 150, rate: 600 };

export function emptyState() {
  return {
    status: null,
    config: null,
    sensors: {},
    stats: [],
    system: [],
    alerts: [],
    log: [],
    rate: [],
    totals: { msgs: 0, bytes: 0, since: Date.now() },
    lastMsgAt: 0,
  };
}

function push(arr, item, limit) {
  arr.push(item);
  if (arr.length > limit) arr.splice(0, arr.length - limit);
}

// msg = { topic, payload (parsed JSON or string), size, t (ms) }
export function applyMessage(state, msg) {
  const { topic, payload: p, size, t } = msg;
  state.totals.msgs += 1;
  state.totals.bytes += size;
  state.lastMsgAt = t;
  push(state.log, msg, LIMITS.log);

  if (typeof p !== "object" || p === null) return state;
  const parts = topic.split("/");
  if (topic === "cloud/edge/stats") push(state.stats, p, LIMITS.stats);
  else if (topic === "cloud/edge/system") push(state.system, p, LIMITS.system);
  else if (topic === "cloud/edge/status") state.status = { ...p, at: t };
  else if (topic === "cloud/edge/config") state.config = p;
  else if (topic === "cloud/alerts") push(state.alerts, p, LIMITS.alerts);
  else if (parts.length === 2 && typeof p.value === "number") {
    const name = parts[1];
    if (!state.sensors[name]) state.sensors[name] = [];
    push(state.sensors[name], { ts: p.ts || t / 1000, v: p.value, min: p.min, max: p.max, n: p.n, method: p.method }, LIMITS.sensor);
  }
  return state;
}

// rate = { ts, msgs, bytes } : traffic measured at the cloud broker side
export function applyRate(state, rate) {
  push(state.rate, rate, LIMITS.rate);
  return state;
}
