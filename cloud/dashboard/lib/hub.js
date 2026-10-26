// Server-side MQTT hub: one subscription to the cloud broker shared by every browser (SSE).
import fs from "node:fs";
import path from "node:path";
import mqtt from "mqtt";
import { applyMessage, applyRate, emptyState } from "./reduce.js";

const STATE_FILE = path.join(process.cwd(), "data", "state.json");

function createHub() {
  let state = emptyState();
  try {
    state = { ...state, ...JSON.parse(fs.readFileSync(STATE_FILE, "utf8")) };
  } catch {}

  const listeners = new Set();
  const emit = (event) => listeners.forEach((fn) => fn(event));
  let second = { msgs: 0, bytes: 0 };

  const client = mqtt.connect(process.env.MQTT_URL || "mqtt://127.0.0.1:1883", {
    username: process.env.MQTT_USER,
    password: process.env.MQTT_PASS,
    clientId: `cloud-dashboard-${process.pid}`,
    reconnectPeriod: 2000,
  });
  client.on("connect", () => {
    console.log("[hub] connected to cloud broker");
    client.subscribe("cloud/#");
  });
  client.on("error", (e) => console.error("[hub]", e.message));
  client.on("message", (topic, buf, packet) => {
    let payload = buf.toString();
    try {
      payload = JSON.parse(payload);
    } catch {}
    // size of the MQTT PUBLISH packet as seen by the broker
    const size = 2 + 2 + Buffer.byteLength(topic) + buf.length;
    const msg = { topic, payload, size, t: Date.now(), retained: packet.retain };
    if (!packet.retain) {
      second.msgs += 1;
      second.bytes += size;
    }
    applyMessage(state, msg);
    emit({ type: "msg", msg });
  });

  setInterval(() => {
    const rate = { ts: Date.now() / 1000, ...second };
    second = { msgs: 0, bytes: 0 };
    applyRate(state, rate);
    emit({ type: "rate", rate });
  }, 1000).unref();

  setInterval(() => {
    fs.mkdir(path.dirname(STATE_FILE), { recursive: true }, () =>
      fs.writeFile(STATE_FILE, JSON.stringify({ ...state, log: [] }), () => {})
    );
  }, 20000).unref();

  return {
    get state() {
      return state;
    },
    subscribe(fn) {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
  };
}

export function getHub() {
  if (!globalThis.__iotHub) globalThis.__iotHub = createHub();
  return globalThis.__iotHub;
}
