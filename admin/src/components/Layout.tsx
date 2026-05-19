import { NavLink, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getHealth } from "@/api/endpoints";
import { getReviewer, setReviewer } from "@/utils";
import { useState } from "react";
import { classNames } from "@/utils";

const nav = [
  { to: "/", label: "대시보드", end: true },
  { to: "/documents", label: "문서" },
  { to: "/candidates", label: "후보 검수 ★" },
  { to: "/ontology", label: "Ontology" },
  { to: "/graph", label: "Graph" },
  { to: "/qa", label: "QA" },
  { to: "/audit", label: "Audit" },
];

function HealthBadge() {
  const { data } = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    refetchInterval: 15_000,
  });
  if (!data) {
    return <span className="badge bg-slate-200 text-slate-600">health …</span>;
  }
  const ok = data.status === "ok";
  return (
    <div className="flex items-center gap-2 text-xs">
      <span
        className={classNames(
          "badge",
          ok ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700",
        )}
      >
        {ok ? "ALL OK" : "DEGRADED"}
      </span>
      {(["postgres", "neo4j", "qdrant"] as const).map((s) => (
        <span
          key={s}
          className={classNames(
            "badge",
            data.services[s] === "ok"
              ? "bg-emerald-50 text-emerald-700"
              : "bg-red-50 text-red-700",
          )}
        >
          {s}
        </span>
      ))}
    </div>
  );
}

function ReviewerInput() {
  const [name, setName] = useState(getReviewer());
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-slate-500">reviewer</span>
      <input
        value={name}
        onChange={(e) => {
          setName(e.target.value);
          setReviewer(e.target.value);
        }}
        className="w-28 rounded border border-slate-300 px-2 py-1 text-xs"
      />
    </div>
  );
}

export default function Layout() {
  return (
    <div className="flex h-full min-h-screen">
      <aside className="w-56 shrink-0 border-r border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-4 py-4">
          <div className="text-sm font-semibold text-slate-900">
            Ontology RAG
          </div>
          <div className="text-[11px] text-slate-500">Governance Admin</div>
        </div>
        <nav className="flex flex-col gap-1 p-2">
          {nav.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                classNames(
                  "rounded-md px-3 py-2 text-sm",
                  isActive
                    ? "bg-brand-50 font-semibold text-brand-700"
                    : "text-slate-700 hover:bg-slate-100",
                )
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
          <HealthBadge />
          <ReviewerInput />
        </header>
        <main className="min-w-0 flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
