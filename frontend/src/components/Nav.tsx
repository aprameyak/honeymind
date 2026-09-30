"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Overview" },
  { href: "/live", label: "Live Sessions" },
  { href: "/sessions", label: "Session Explorer" },
  { href: "/clusters", label: "Clusters" },
  { href: "/anomalies", label: "Anomalies" },
  { href: "/experiments", label: "Experiments" },
  { href: "/analysis", label: "AI Analysis" },
];

export function Nav() {
  const path = usePathname();
  return (
    <header className="border-b border-line/80 bg-panel/70 backdrop-blur sticky top-0 z-40">
      <div className="mx-auto max-w-7xl px-4 py-3 flex items-center gap-6">
        <Link href="/" className="font-display text-xl font-bold tracking-tight text-accent">
          HoneyMind
        </Link>
        <nav className="flex flex-wrap gap-1 text-sm">
          {links.map((l) => {
            const active = path === l.href || (l.href !== "/" && path.startsWith(l.href));
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`px-2.5 py-1.5 transition ${
                  active ? "text-white border-b-2 border-accent" : "text-mute hover:text-white"
                }`}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>
        <div className="ml-auto text-xs font-mono text-mute flex items-center gap-2">
          <span className="inline-block h-2 w-2 rounded-full bg-accent animate-live" />
          LAB CONTAINED
        </div>
      </div>
    </header>
  );
}
