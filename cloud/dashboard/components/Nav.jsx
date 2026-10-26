"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLive } from "./LiveProvider";

const LINKS = [
  ["/", "Overview"],
  ["/throughput", "Throughput"],
  ["/3d", "3D view"],
  ["/edge", "Raspberry Pi"],
  ["/messages", "MQTT log"],
];

export default function Nav() {
  const path = usePathname();
  const { state, connected } = useLive();
  const edgeOnline = state.status && state.status.state === "online";
  return (
    <header className="nav">
      <div className="brand">
        <span className="logo" aria-hidden>◈</span>
        <div>
          <strong>IoT Cloud</strong>
          <small>EC2 · MQTT · Edge computing</small>
        </div>
      </div>
      <nav>
        {LINKS.map(([href, label]) => (
          <Link key={href} href={href} className={path === href ? "active" : ""}>
            {label}
          </Link>
        ))}
      </nav>
      <div className="pills">
        <span className={`pill ${connected ? "ok" : "bad"}`}>{connected ? "● Live" : "○ Reconnecting"}</span>
        <span className={`pill ${edgeOnline ? "ok" : "bad"}`}>{edgeOnline ? "● Pi online" : "○ Pi offline"}</span>
      </div>
    </header>
  );
}
