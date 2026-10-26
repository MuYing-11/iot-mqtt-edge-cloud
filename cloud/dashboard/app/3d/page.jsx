"use client";
import { useMemo } from "react";
import Chart, { ink } from "@/components/Chart";
import { useLive } from "@/components/LiveProvider";
import { SENSORS } from "@/lib/reduce";

const axis = (name) => ({
  name, type: "value", scale: true,
  nameTextStyle: { color: ink.secondary },
  axisLabel: { color: ink.muted, fontSize: 10 },
  axisLine: { lineStyle: { color: "#55554f" } },
  splitLine: { lineStyle: { color: "#2c2c28" } },
});

// align the reduced series on their timestamps (same edge period for all sensors)
function joined(sensors, keys, n) {
  const maps = keys.map((k) => new Map((sensors[k] || []).slice(-n).map((p) => [Math.round(p.ts), p.v])));
  const out = [];
  for (const [ts, v0] of maps[0]) {
    const rest = maps.slice(1).map((m) => m.get(ts) ?? m.get(ts - 1) ?? m.get(ts + 1));
    if (rest.every((v) => v != null)) out.push([v0, ...rest, ts]);
  }
  return out;
}

export default function ThreeD() {
  const { state } = useLive();

  const trajectory = useMemo(() => {
    const pts = joined(state.sensors, ["temperature", "humidity", "co2"], 400);
    const t0 = pts.length ? pts[0][3] : 0;
    return {
      backgroundColor: "transparent",
      tooltip: { formatter: (p) => `T ${p.value[0].toFixed(2)} °C<br/>H ${p.value[1].toFixed(2)} %<br/>CO₂ ${p.value[2].toFixed(0)} ppm` },
      visualMap: { show: true, dimension: 3, min: t0, max: pts.length ? pts[pts.length - 1][3] : 1, calculable: false,
        inRange: { color: ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab"] }, text: ["recent", "older"],
        textStyle: { color: ink.muted }, left: 8, bottom: 8, itemHeight: 90 },
      xAxis3D: axis("Temperature °C"), yAxis3D: axis("Humidity %"), zAxis3D: axis("CO₂ ppm"),
      grid3D: { boxWidth: 110, boxDepth: 110, boxHeight: 80, viewControl: { autoRotate: true, autoRotateSpeed: 6, distance: 230 },
        light: { main: { intensity: 1.1 }, ambient: { intensity: 0.4 } }, axisPointer: { lineStyle: { color: ink.muted } } },
      series: [
        { type: "line3D", data: pts, lineStyle: { width: 2, opacity: 0.6 } },
        { type: "scatter3D", data: pts, symbolSize: 5 },
      ],
    };
  }, [state.sensors]);

  const surface = useMemo(() => {
    const keys = Object.keys(SENSORS).filter((k) => state.sensors[k]?.length);
    const N = 60;
    const data = [];
    keys.forEach((k, yi) => {
      const pts = state.sensors[k].slice(-N);
      const vals = pts.map((p) => p.v);
      const mean = vals.reduce((a, b) => a + b, 0) / (vals.length || 1);
      const sd = Math.sqrt(vals.reduce((a, b) => a + (b - mean) ** 2, 0) / (vals.length || 1)) || 1;
      pts.forEach((p, xi) => data.push({ value: [xi + (N - pts.length), yi, (p.v - mean) / sd], itemStyle: { color: SENSORS[k].color } }));
    });
    return {
      backgroundColor: "transparent",
      tooltip: { formatter: (p) => `${SENSORS[keys[p.value[1]]].label}<br/>z-score ${p.value[2].toFixed(2)}` },
      xAxis3D: { ...axis("time (last 60 periods)"), type: "value", min: 0, max: N },
      yAxis3D: { ...axis(""), type: "category", data: keys.map((k) => SENSORS[k].label) },
      zAxis3D: { ...axis("z-score"), min: -3, max: 3 },
      grid3D: { boxWidth: 200, boxDepth: 70, boxHeight: 60, viewControl: { alpha: 22, beta: 28, distance: 240 },
        light: { main: { intensity: 1.2, shadow: false }, ambient: { intensity: 0.35 } } },
      series: [{ type: "bar3D", data, shading: "lambert", barSize: [2.4, 8], label: { show: false } }],
    };
  }, [state.sensors]);

  const has = Object.keys(state.sensors).length > 0;
  return (
    <>
      <h1>3D view</h1>
      <p className="sub">Left: trajectory of the system state (temperature, humidity, CO₂) over time. Right: normalised history of every sensor (z-score per sensor). Drag to rotate, scroll to zoom.</p>
      {has ? (
        <div className="grid two">
          <div className="card"><h2>State-space trajectory</h2><Chart option={trajectory} height={520} gl /></div>
          <div className="card"><h2>Sensor history (z-score bars)</h2><Chart option={surface} height={520} gl /></div>
        </div>
      ) : <div className="card empty">Waiting for sensor data from the edge…</div>}
    </>
  );
}
