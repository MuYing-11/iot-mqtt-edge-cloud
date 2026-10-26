"use client";
import { useMemo } from "react";
import Chart, { baseOption, ink } from "@/components/Chart";
import { useLive } from "@/components/LiveProvider";
import { fmtDuration, fmtTime, gapped, last } from "@/lib/format";

function gauge(value, name, color) {
  return {
    backgroundColor: "transparent",
    series: [{
      type: "gauge", startAngle: 210, endAngle: -30, min: 0, max: 100, radius: "92%",
      progress: { show: true, width: 12, roundCap: true, itemStyle: { color } },
      axisLine: { lineStyle: { width: 12, color: [[1, "#2c2c28"]] }, roundCap: true },
      axisTick: { show: false }, splitLine: { show: false }, pointer: { show: false },
      axisLabel: { show: false },
      title: { offsetCenter: [0, "38%"], color: ink.muted, fontSize: 12 },
      detail: { offsetCenter: [0, "-4%"], color: ink.primary, fontSize: 26, formatter: "{value}%" },
      data: [{ value: value ?? 0, name }],
    }],
  };
}

export default function Edge() {
  const { state } = useLive();
  const sys = last(state.system);
  const stats = last(state.stats);

  const history = useMemo(() => baseOption({
    tooltip: { ...baseOption().tooltip, valueFormatter: (v) => `${v} %` },
    yAxis: { ...baseOption().yAxis, scale: false, min: 0, max: 100, name: "%", nameTextStyle: { color: ink.muted } },
    series: [
      { name: "CPU", type: "line", showSymbol: false, lineStyle: { width: 2, color: "#3987e5" }, itemStyle: { color: "#3987e5" },
        data: gapped(state.system.map((s) => [s.ts * 1000, s.cpu_pct]), 20000) },
      { name: "Memory", type: "line", showSymbol: false, lineStyle: { width: 2, color: "#d95926" }, itemStyle: { color: "#d95926" },
        data: gapped(state.system.map((s) => [s.ts * 1000, s.mem_used_pct]), 20000) },
    ],
  }), [state.system]);

  const cpuG = useMemo(() => gauge(sys?.cpu_pct, "CPU", "#3987e5"), [sys]);
  const memG = useMemo(() => gauge(sys?.mem_used_pct, "Memory", "#d95926"), [sys]);

  return (
    <>
      <h1>Raspberry Pi edge node</h1>
      <p className="sub">Health of the edge gateway, reported every 5 s on <span className="mono">cloud/edge/system</span>.</p>
      <div className="grid kpis">
        <div className="card kpi"><div className="label">Hostname</div><div className="value" style={{ fontSize: 20 }}>{sys?.host ?? "–"}</div><div className="hint">{sys ? `${sys.cpus} CPU cores` : ""}</div></div>
        <div className="card kpi"><div className="label">System uptime</div><div className="value" style={{ fontSize: 20 }}>{fmtDuration(sys?.uptime_s)}</div><div className="hint">load average {sys?.load1 ?? "–"}</div></div>
        <div className="card kpi"><div className="label">Gateway status</div><div className="value" style={{ fontSize: 20 }}>{state.status?.state ?? "–"}</div><div className="hint">MQTT last will on cloud/edge/status</div></div>
        <div className="card kpi"><div className="label">Filter configuration</div><div className="value" style={{ fontSize: 20 }}>{state.config?.mode ?? "–"}</div><div className="hint">{state.config ? `period ${state.config.period}s · window ${state.config.window} samples` : ""}</div></div>
      </div>
      <div className="grid two">
        <div className="card">
          <h2>Current load</h2>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr" }}>
            <Chart option={cpuG} height={210} />
            <Chart option={memG} height={210} />
          </div>
        </div>
        <div className="card"><h2>CPU and memory history</h2><Chart option={history} height={230} /></div>
      </div>
      <div className="card" style={{ marginTop: 14 }}>
        <h2>Last gateway statistics</h2>
        {stats ? (
          <table><tbody>
            {Object.entries(stats).map(([k, v]) => (
              <tr key={k}><td className="mono" style={{ width: 220, color: "var(--muted)" }}>{k}</td><td className="mono">{k === "ts" ? fmtTime(v) : String(v)}</td></tr>
            ))}
          </tbody></table>
        ) : <div className="meta">No statistics yet.</div>}
      </div>
    </>
  );
}
