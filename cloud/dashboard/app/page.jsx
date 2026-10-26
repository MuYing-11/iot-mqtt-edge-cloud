"use client";
import { useMemo } from "react";
import Chart, { baseOption } from "@/components/Chart";
import { useLive } from "@/components/LiveProvider";
import { SENSORS } from "@/lib/reduce";
import { avg, fmtDuration, fmtTime, gapped, last } from "@/lib/format";

function SensorCard({ name, series }) {
  const meta = SENSORS[name] || { label: name, unit: "", color: "#9085e9" };
  const now = last(series);
  const option = useMemo(() => {
    const pts = series.slice(-300);
    const hasBand = pts.some((p) => p.min != null);
    const s = [
      {
        name: "Edge value",
        type: "line",
        showSymbol: false,
        lineStyle: { width: 2, color: meta.color },
        itemStyle: { color: meta.color },
        data: gapped(pts.map((p) => [p.ts * 1000, p.v])),
        z: 3,
      },
    ];
    if (hasBand) {
      s.push(
        { name: "min", type: "line", stack: "band", showSymbol: false, lineStyle: { opacity: 0 }, tooltip: { show: false },
          data: gapped(pts.map((p) => [p.ts * 1000, p.min ?? p.v])) },
        { name: "Raw min–max", type: "line", stack: "band", showSymbol: false, lineStyle: { opacity: 0 },
          areaStyle: { color: meta.color, opacity: 0.18 }, itemStyle: { color: meta.color },
          data: gapped(pts.map((p) => [p.ts * 1000, (p.max ?? p.v) - (p.min ?? p.v)])) }
      );
    }
    return baseOption({
      legend: { show: false },
      grid: { left: 48, right: 12, top: 10, bottom: 26 },
      tooltip: { ...baseOption().tooltip, valueFormatter: (v) => (v == null ? "–" : v.toFixed(2)) },
      series: s,
    });
  }, [series, meta.color]);

  return (
    <div className="card">
      <div className="sensor-head">
        <h2><span className="swatch" style={{ background: meta.color }} />{meta.label}</h2>
        <div className="now">{now ? now.v.toFixed(2) : "–"} <small>{meta.unit}</small></div>
      </div>
      <div className="meta">
        {now ? `${now.method || ""} · ${now.n ?? 1} raw samples fused · min ${now.min?.toFixed(2) ?? "–"} / max ${now.max?.toFixed(2) ?? "–"}` : "waiting for data"}
      </div>
      <Chart option={option} height={200} />
    </div>
  );
}

export default function Overview() {
  const { state } = useLive();
  const stats = last(state.stats);
  const fresh = stats && Date.now() / 1000 - stats.ts < 5;
  const online = state.status && state.status.state === "online";
  const names = Object.keys(state.sensors).sort((a, b) => Object.keys(SENSORS).indexOf(a) - Object.keys(SENSORS).indexOf(b));
  const activeAlarms = Object.values(
    state.alerts.reduce((acc, a) => ({ ...acc, [a.sensor]: a }), {})
  ).filter((a) => a.state === "ALARM");

  return (
    <>
      <h1>Overview</h1>
      <p className="sub">Reduced data published by the Raspberry Pi edge gateway and received by the MQTT broker on EC2.</p>

      <div className="grid kpis">
        <div className="card kpi">
          <div className="label">Edge node</div>
          <div className="value" style={{ color: online ? "#7bd87b" : "#ef8a8a" }}>{online ? "Online" : "Offline"}</div>
          <div className="hint">{stats ? `gateway uptime ${fmtDuration(stats.uptime)}` : "no stats yet"}</div>
        </div>
        <div className="card kpi">
          <div className="label">Sensor traffic into the edge</div>
          <div className="value">{fresh ? stats.in_msgs_s : 0}<small>msg/s</small></div>
          <div className="hint">avg {avg(state.stats, "in_msgs_s").toFixed(1)} msg/s (30 s)</div>
        </div>
        <div className="card kpi">
          <div className="label">Traffic sent to the cloud</div>
          <div className="value">{fresh ? stats.out_msgs_s : 0}<small>msg/s</small></div>
          <div className="hint">avg {avg(state.stats, "out_msgs_s").toFixed(1)} msg/s (30 s)</div>
        </div>
        <div className="card kpi">
          <div className="label">Bandwidth saved by the edge</div>
          <div className="value">{stats ? stats.reduction_pct.toFixed(1) : "–"}<small>%</small></div>
          <div className="hint">bytes out vs bytes in, since gateway start</div>
        </div>
        <div className="card kpi">
          <div className="label">Edge filter</div>
          <div className="value" style={{ fontSize: 20 }}>{state.config ? state.config.mode : "–"}</div>
          <div className="hint">{state.config ? `period ${state.config.period}s · window ${state.config.window}` : ""}</div>
        </div>
        <div className="card kpi">
          <div className="label">Active alarms</div>
          <div className="value" style={{ color: activeAlarms.length ? "#ff9b9b" : undefined }}>{activeAlarms.length}</div>
          <div className="hint">{activeAlarms.map((a) => a.sensor).join(", ") || "all sensors below threshold"}</div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 14 }}>
        <h2>Data path</h2>
        <div className="pipeline">
          <div className="node"><b>Sensors</b><span>PyQt6 simulator · PC</span><div className="rate">{fresh ? stats.in_msgs_s : 0} msg/s raw</div></div>
          <div className={`link ${fresh && stats.in_msgs_s ? "live" : ""}`} />
          <div className="node"><b>Raspberry Pi</b><span>Mosquitto + edge filter</span><div className="rate">{state.config ? state.config.mode : "–"}</div></div>
          <div className={`link out ${fresh && stats.out_msgs_s ? "live" : ""}`} />
          <div className="node"><b>EC2 broker</b><span>Mosquitto · port 1883</span><div className="rate">{fresh ? stats.out_msgs_s : 0} msg/s reduced</div></div>
          <div className={`link out ${Date.now() - state.lastMsgAt < 3000 ? "live" : ""}`} />
          <div className="node"><b>Dashboard</b><span>Next.js · SSE</span><div className="rate">{state.totals.msgs} msgs received</div></div>
        </div>
      </div>

      {names.length ? (
        <div className="grid sensors">
          {names.map((n) => <SensorCard key={n} name={n} series={state.sensors[n]} />)}
        </div>
      ) : (
        <div className="card empty">No sensor data yet. Start the simulator on the PC: it publishes to the Pi, which forwards reduced data here.</div>
      )}

      <div className="card" style={{ marginTop: 14 }}>
        <h2>Edge alerts (threshold detection on the Raspberry Pi)</h2>
        {state.alerts.length ? (
          <table>
            <thead><tr><th>Time</th><th>Sensor</th><th>Value</th><th>Limit</th><th>State</th></tr></thead>
            <tbody>
              {state.alerts.slice(-12).reverse().map((a, i) => (
                <tr key={i}>
                  <td className="mono">{fmtTime(a.ts)}</td><td>{a.sensor}</td><td className="mono">{a.value}</td>
                  <td className="mono">{a.limit}</td>
                  <td><span className={`tag ${a.state === "ALARM" ? "alarm" : "ok"}`}>{a.state === "ALARM" ? "▲ ALARM" : "✓ OK"}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <div className="meta">No alert so far.</div>}
      </div>
    </>
  );
}
