"use client";
import { useLive } from "@/components/LiveProvider";
import { fmtBytes } from "@/lib/format";

export default function Messages() {
  const { state } = useLive();
  const log = state.log.slice(-80).reverse();
  return (
    <>
      <h1>MQTT log</h1>
      <p className="sub">Last messages received by the EC2 broker on <span className="mono">cloud/#</span> — {state.totals.msgs} messages, {fmtBytes(state.totals.bytes)} since the dashboard started.</p>
      <div className="card">
        {log.length ? (
          <table>
            <thead><tr><th style={{ width: 100 }}>Time</th><th style={{ width: 190 }}>Topic</th><th style={{ width: 70 }}>Size</th><th>Payload</th></tr></thead>
            <tbody>
              {log.map((m, i) => (
                <tr key={`${m.t}-${i}`}>
                  <td className="mono">{new Date(m.t).toLocaleTimeString()}</td>
                  <td className="mono">{m.topic}{m.retained ? " (retained)" : ""}</td>
                  <td className="mono">{m.size} B</td>
                  <td className="mono payload">{typeof m.payload === "string" ? m.payload : JSON.stringify(m.payload)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <div className="empty">No message yet.</div>}
      </div>
    </>
  );
}
