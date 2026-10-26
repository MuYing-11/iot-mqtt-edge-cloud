"use client";
import { useEffect, useRef } from "react";

// Thin ECharts wrapper. gl=true loads echarts-gl for the 3D views.
export default function Chart({ option, height = 280, gl = false, className = "" }) {
  const el = useRef(null);
  const chart = useRef(null);
  const latest = useRef(option);
  latest.current = option;

  useEffect(() => {
    let disposed = false;
    let observer;
    (async () => {
      const echarts = await import("echarts");
      if (gl) await import("echarts-gl");
      if (disposed || !el.current) return;
      chart.current = echarts.init(el.current, null, { renderer: "canvas" });
      chart.current.setOption(latest.current);
      observer = new ResizeObserver(() => chart.current && chart.current.resize());
      observer.observe(el.current);
    })();
    return () => {
      disposed = true;
      observer && observer.disconnect();
      chart.current && chart.current.dispose();
      chart.current = null;
    };
  }, [gl]);

  useEffect(() => {
    if (chart.current) chart.current.setOption(option, { lazyUpdate: true });
  }, [option]);

  return <div ref={el} className={className} style={{ width: "100%", height }} />;
}

// Common styling for the dark dashboard surface.
export const ink = { primary: "#f0efec", secondary: "#c3c2b7", muted: "#8a8981", grid: "#33332f" };

export function baseOption(extra = {}) {
  return {
    backgroundColor: "transparent",
    animation: false,
    textStyle: { color: ink.secondary, fontFamily: "inherit" },
    grid: { left: 56, right: 18, top: 36, bottom: 30 },
    tooltip: {
      trigger: "axis",
      backgroundColor: "#24241f",
      borderColor: "#3a3a35",
      textStyle: { color: ink.primary },
      axisPointer: { type: "line", lineStyle: { color: ink.muted } },
    },
    legend: { top: 4, right: 8, textStyle: { color: ink.secondary }, icon: "roundRect", itemWidth: 12, itemHeight: 4 },
    xAxis: {
      type: "time",
      axisLine: { lineStyle: { color: ink.grid } },
      axisLabel: { color: ink.muted, hideOverlap: true },
      splitLine: { show: false },
    },
    yAxis: {
      type: "value",
      scale: true,
      axisLabel: { color: ink.muted },
      splitLine: { lineStyle: { color: ink.grid, type: "dashed" } },
    },
    ...extra,
  };
}
