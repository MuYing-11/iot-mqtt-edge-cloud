"use client";
import { useMemo } from "react";
import Chart, { baseOption, ink } from "@/components/Chart";
import { useLive } from "@/components/LiveProvider";
import { avg, fmtBytes, gapped, last } from "@/lib/format";

const IN = "#3987e5";
const OUT = "#d95926";

function lines(series, unit) {
  return baseOption({
    tooltip: { ...baseOption().tooltip, valueFormatter: (v) => `${v} ${unit}` },
    yAxis: { ...baseOption().yAxis, scale: false, name: unit, nameTextStyle: { color: ink.muted } },
    series: series.map((s) => ({
      type: "line", showSymbol: false, smooth: false, step: "end",
      lineStyle: { width: 2, color: s.color }, itemStyle: { color: s.color },
      areaStyle: s.area ? { color: s.color, opacity: 0.12 } : undefined,
      ...s,
      data: gapped(s.data),
    })),
  });
}

export default function Throughput() {
  const { state } = useLive();
  const stats = state.stats.slice(-300);
  const s = last(state.stats);

  const bytesOpt = useMemo(() => lines([
    { name: "Sensors → edge (raw)", color: IN, area: true, data: stats.map((x) => [x.ts * 1000, x.in_bytes_s]) },
    { name: "Edge → cloud (reduced)", color: OUT, area: true, data: stats.map((x) => [x.ts * 1000, x.out_bytes_s]) },
  ], "B/s"), [state.stats]); // eslint-disable-line react-hooks/exhaustive-deps

  const msgsOpt = useMemo(() => lines([
    { name: "Sensors → edge", color: IN, data: stats.map((x) => [x.ts * 1000, x.in_msgs_s]) },
    { name: "Edge → cloud", color: OUT, data: stats.map((x) => [x.ts * 1000, x.out_msgs_s]) },
  ], "msg/s"), [state.stats]); // eslint-disable-line react-hooks/exhaustive-deps

  const cloudOpt = useMemo(() => lines([
    { name: "Received by EC2 dashboard (all cloud/# topics)", color: "#9085e9", area: true,
      data: state.rate.slice(-300).map((x) => [x.ts * 1000, x.bytes]) },
  ], "B/s"), [state.rate]);

  const reductionOpt = useMemo(() => baseOption({
    legend: { show: false },
    tooltip: { ...baseOption().tooltip, valueFormatter: (v) => `${v} %` },
    yAxis: { ...baseOption().yAxis, scale: false, max: 100, min: 0, name: "%", nameTextStyle: { color: ink.muted } },
    series: [{ name: "Cumulative reduction", type: "line", showSymbol: false, lineStyle: { width: 2, color: "#199e70" },
      itemStyle: { color: "#199e70" }, data: gapped(stats.map((x) => [x.ts * 1000, x.reduction_pct])) }],
  }), [state.stats]); // eslint-disable-line react-hooks/exhaustive-deps

  const inAvg = avg(state.stats, "in_bytes_s");
  const outAvg = avg(state.stats, "out_bytes_s");

  return (
    <>
      <h1>Throughput</h1>
      <p className="sub">Bandwidth before and after the edge filter (MQTT PUBLISH packet sizes measured on the Raspberry Pi), and traffic measured on arrival at EC2.</p>
      <div className="grid kpis">
        <div className="card kpi"><div className="label">Raw ingress (30 s avg)</div><div className="value">{fmtBytes(inAvg)}<small>/s</small></div><div className="hint">{avg(state.stats, "in_msgs_s").toFixed(1)} msg/s from the sensors</div></div>
        <div className="card kpi"><div className="label">Reduced egress (30 s avg)</div><div className="value">{fmtBytes(outAvg)}<small>/s</small></div><div className="hint">{avg(state.stats, "out_msgs_s").toFixed(1)} msg/s to EC2</div></div>
        <div className="card kpi"><div className="label">Instant gain</div><div className="value">{inAvg ? (100 * (1 - outAvg / inAvg)).toFixed(1) : "–"}<small>%</small></div><div className="hint">1 − out/in over the last 30 s</div></div>
        <div className="card kpi"><div className="label">Total in / out</div><div className="value" style={{ fontSize: 20 }}>{fmtBytes(s?.total_in_bytes)} / {fmtBytes(s?.total_out_bytes)}</div><div className="hint">{s?.total_in_msgs ?? 0} → {s?.total_out_msgs ?? 0} messages</div></div>
      </div>
      <div className="grid two">
        <div className="card"><h2>Bytes per second</h2><Chart option={bytesOpt} height={300} /></div>
        <div className="card"><h2>Messages per second</h2><Chart option={msgsOpt} height={300} /></div>
        <div className="card"><h2>Ingress measured at the cloud (EC2)</h2><Chart option={cloudOpt} height={260} /></div>
        <div className="card"><h2>Cumulative bandwidth reduction</h2><Chart option={reductionOpt} height={260} /></div>
      </div>
    </>
  );
}
