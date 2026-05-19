import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { listAuditLogs } from "@/api/endpoints";
import StatusBadge from "@/components/StatusBadge";
import JsonViewer from "@/components/JsonViewer";
import { downloadJson, formatDate, shortId } from "@/utils";
import type { AuditLog } from "@/api/types";

const actions = [
  "",
  "DOC_UPLOAD",
  "EXTRACTION_RUN",
  "REVIEW_APPROVE",
  "REVIEW_REJECT",
  "REVIEW_MODIFY",
  "REVIEW_MERGE",
  "SCHEMA_CHANGE",
  "GRAPH_SYNC",
  "QUERY",
];

export default function Audit() {
  const [action, setAction] = useState("");
  const [targetType, setTargetType] = useState("");
  const [selected, setSelected] = useState<AuditLog | null>(null);

  const list = useQuery({
    queryKey: ["audit", action, targetType],
    queryFn: () =>
      listAuditLogs({
        action: action || undefined,
        target_type: targetType || undefined,
        limit: 200,
      }),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Audit Log</h1>
          <p className="text-sm text-slate-500">모든 거버넌스 액션의 영속 기록.</p>
        </div>
        <button
          className="btn-ghost"
          onClick={() => downloadJson(`audit-${Date.now()}.json`, list.data ?? [])}
          disabled={!list.data?.length}
        >
          JSON export
        </button>
      </div>

      <div className="card flex flex-wrap items-end gap-3 p-3">
        <div>
          <label className="label">action</label>
          <select
            className="input w-48"
            value={action}
            onChange={(e) => setAction(e.target.value)}
          >
            {actions.map((a) => (
              <option key={a || "all"} value={a}>
                {a || "(전체)"}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">target_type</label>
          <input
            className="input w-48"
            placeholder="entity / relation / document …"
            value={targetType}
            onChange={(e) => setTargetType(e.target.value)}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_440px]">
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2">action</th>
                <th className="px-3 py-2">target</th>
                <th className="px-3 py-2">actor</th>
                <th className="px-3 py-2">at</th>
              </tr>
            </thead>
            <tbody>
              {(list.data ?? []).map((row) => (
                <tr
                  key={row.id}
                  className={
                    "cursor-pointer border-t border-slate-100 " +
                    (selected?.id === row.id ? "bg-brand-50" : "hover:bg-slate-50")
                  }
                  onClick={() => setSelected(row)}
                >
                  <td className="px-3 py-2"><StatusBadge status={row.action} /></td>
                  <td className="px-3 py-2 text-slate-600">
                    {row.target_type ?? "-"}{" "}
                    <span className="font-mono text-xs text-slate-400">
                      {shortId(row.target_id)}
                    </span>
                  </td>
                  <td className="px-3 py-2">{row.actor ?? "-"}</td>
                  <td className="px-3 py-2 text-slate-500">{formatDate(row.created_at)}</td>
                </tr>
              ))}
              {!list.data?.length && !list.isLoading ? (
                <tr>
                  <td colSpan={4} className="py-6 text-center text-xs text-slate-400">
                    audit 기록 없음
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>

        <div className="card p-3">
          <h3 className="text-sm font-semibold">payload</h3>
          {selected ? (
            <div className="mt-2 space-y-3 text-xs">
              <div className="text-slate-500">
                {selected.action} ·{" "}
                <span className="font-mono">{shortId(selected.id)}</span>
              </div>
              {selected.before_json ? (
                <div>
                  <div className="text-xs font-semibold text-slate-700">before</div>
                  <JsonViewer data={selected.before_json} />
                </div>
              ) : null}
              {selected.after_json ? (
                <div>
                  <div className="text-xs font-semibold text-slate-700">after</div>
                  <JsonViewer data={selected.after_json} />
                </div>
              ) : null}
              {selected.metadata_json ? (
                <div>
                  <div className="text-xs font-semibold text-slate-700">metadata</div>
                  <JsonViewer data={selected.metadata_json} />
                </div>
              ) : null}
            </div>
          ) : (
            <div className="mt-2 text-xs text-slate-400">행을 클릭하세요.</div>
          )}
        </div>
      </div>
    </div>
  );
}
