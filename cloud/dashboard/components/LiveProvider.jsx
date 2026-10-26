"use client";
import { createContext, useContext, useEffect, useRef, useState } from "react";
import { applyMessage, applyRate, emptyState } from "@/lib/reduce";

const LiveContext = createContext({ state: emptyState(), connected: false, version: 0 });

export function useLive() {
  return useContext(LiveContext);
}

// One SSE connection for the whole app; React re-renders at most every 500 ms.
export default function LiveProvider({ children }) {
  const stateRef = useRef(emptyState());
  const dirty = useRef(false);
  const [view, setView] = useState({ state: stateRef.current, connected: false, version: 0 });
  const connectedRef = useRef(false);

  useEffect(() => {
    let source;
    let retry;
    const connect = () => {
      source = new EventSource("/api/stream");
      source.onopen = () => {
        connectedRef.current = true;
        dirty.current = true;
      };
      source.onmessage = (e) => {
        const event = JSON.parse(e.data);
        if (event.type === "snapshot") stateRef.current = event.state;
        else if (event.type === "msg") applyMessage(stateRef.current, event.msg);
        else if (event.type === "rate") applyRate(stateRef.current, event.rate);
        dirty.current = true;
      };
      source.onerror = () => {
        connectedRef.current = false;
        dirty.current = true;
        source.close();
        retry = setTimeout(connect, 2000);
      };
    };
    connect();
    const timer = setInterval(() => {
      if (!dirty.current) return;
      dirty.current = false;
      setView((v) => ({ state: { ...stateRef.current }, connected: connectedRef.current, version: v.version + 1 }));
    }, 500);
    return () => {
      clearInterval(timer);
      clearTimeout(retry);
      source && source.close();
    };
  }, []);

  return <LiveContext.Provider value={view}>{children}</LiveContext.Provider>;
}
