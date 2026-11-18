
"use client";

import type { ViewId } from "@/lib/types";

const navigation: Array<{
  id: ViewId;
  label: string;
  icon: string;
}> = [
  { id: "overview", label: "Overview", icon: "grid" },
  { id: "jobs", label: "Discover Jobs", icon: "briefcase" },
  { id: "profile", label: "My Profile", icon: "user" },
  { id: "evaluation", label: "Evaluation Analytics", icon: "chart" },
];

function Icon({ name }: { name: string }) {
  const common = "h-5 w-5";

  if (name === "grid")
    return (
      <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <rect x="3" y="3" width="7" height="7" rx="2" />
        <rect x="14" y="3" width="7" height="7" rx="2" />
        <rect x="3" y="14" width="7" height="7" rx="2" />
        <rect x="14" y="14" width="7" height="7" rx="2" />
      </svg>
    );

  if (name === "briefcase")
    return (
      <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <rect x="3" y="7" width="18" height="13" rx="3" />
        <path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18M10 12v2h4v-2" />
      </svg>
    );

  if (name === "user")
    return (
      <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <circle cx="12" cy="8" r="4" />
        <path d="M4 21a8 8 0 0 1 16 0" />
      </svg>
    );

  return (
    <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />
      <path d="m4 10 6-6 6 9 6-5" />
    </svg>
  );
}

export function Sidebar({
  active,
  onChange,
}: {
  active: ViewId;
  onChange: (view: ViewId) => void;
}) {
  return (
    <aside className="hidden w-64 shrink-0 border-r border-white/7 bg-[#0c1024] lg:flex lg:flex-col">
      <div className="flex h-20 items-center px-7">
        <button
          onClick={() => onChange("overview")}
          className="flex items-center gap-3"
          aria-label="Go to overview"
        >
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-violet-500 to-blue-500 text-sm font-bold shadow-lg shadow-violet-950/30">
            N
          </span>
          <span className="text-lg font-semibold tracking-[0.18em] text-white">
            NEXORA
          </span>
        </button>
      </div>

      <nav className="flex-1 space-y-1 px-4 py-5">
        {navigation.map((item) => (
          <button
            key={item.id}
            onClick={() => onChange(item.id)}
            className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm transition ${
              active === item.id
                ? "bg-violet-500/12 text-violet-200"
                : "text-slate-400 hover:bg-white/4 hover:text-slate-100"
            }`}
          >
            <Icon name={item.icon} />
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="m-4 rounded-2xl border border-white/7 bg-white/[0.025] p-4">
        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
          Career profile
        </p>
        <p className="mt-2 text-sm text-slate-300">
          Configure your preferences
        </p>
      </div>
    </aside>
  );
}

export function MobileNav({
  active,
  onChange,
}: {
  active: ViewId;
  onChange: (view: ViewId) => void;
}) {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-4 border-t border-white/8 bg-[#0c1024]/95 px-2 py-2 backdrop-blur lg:hidden">
      {navigation.map((item) => (
        <button
          key={item.id}
          onClick={() => onChange(item.id)}
          className={`flex min-h-14 flex-col items-center justify-center gap-1 rounded-lg text-[10px] ${
            active === item.id
              ? "text-violet-300"
              : "text-slate-500"
          }`}
        >
          <Icon name={item.icon} />
          <span className="max-w-20 truncate">{item.label}</span>
        </button>
      ))}
    </nav>
  );
}
