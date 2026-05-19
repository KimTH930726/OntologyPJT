import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  getGraphEntity,
  getSubgraph,
  listEntityCandidates,
  listSyncLogs,
  syncAll,
} from "@/api/endpoints";
import { apiErrorMessage } from "@/api/client";
import GraphCanvas from "@/components/GraphCanvas";
import StatusBadge from "@/components/StatusBadge";
import { formatDate, shortId } from "@/utils";
import type { GraphNode } from "@/api/types";

export default function Graph() {
  const [seedInput, setSeedInput] = useState("");
  const [seed, setSeed] = useState("");
  const [depth, setDepth] = useState(2);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<GraphNode | null>(null);

  const approvedEnts = useQuery({
    queryKey: ["g-approved-ents"],
    queryFn: () => listEntityCandidates({ review_status: "APPROVED", limit: 500 }),
  });
  const suggestions = Array.from(
    new Set((approvedEnts.data ?? []).map((e) => e.normalized_name)),
  ).slice(0, 50);

  const sub = useQuery({
    queryKey: ["subgraph", seed, depth],
    queryFn: () => getSubgraph(seed, depth),
    enabled: !!seed,
    retry: false,
  });

  const entity = useQuery({
    queryKey: ["graph-entity", selected?.normalized_name],
    queryFn: () => getGraphEntity(selected!.normalized_name),
    enabled: !!selected,
    retry: false,
  });

  const sync = useMutation({
    mutationFn: () => syncAll(false),
    onError: (e) => setError(apiErrorMessage(e)),
  });

  const syncLogs = useQuery({
    queryKey: ["sync-logs"],
    queryFn: () => listSyncLogs({ limit: 10 }),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Graph</h1>
          <p className="text-sm text-slate-500">
            APPROVED 노드 시각화 + 1~5 depth subgraph 탐색.
          </p>
        </div>
        <div className="flex gap-2">
          <button className="btn-ghost" onClick={() => sync.mutate()} disabled={sync.isPending}>
            {sync.isPending ? "동기화 중…" : "Neo4j sync 실행"}
          </button>
        </div>
      </div>

      {sync.data ? (
        <div className="rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-700">
          sync OK · entities: {sync.data.entity_success}/{sync.data.entity_failed}f/
          {sync.data.entity_skipped}s · relations: {sync.data.relation_success}/
          {sync.data.relation_failed}f/{sync.data.relation_skipped}s
        </div>
      ) : null}

      <div className="card flex flex-wrap items-end gap-3 p-3">
        <div className="w-72">
          <label className="label">seed (normalized_name)</label>
          <input
            list="seed-suggestions"
            className="input"
            placeholder="FullCancelPolicy"
            value={seedInput}
            onChange={(e) => setSeedInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && seedInput) setSeed(seedInput);
            }}
          />
          <datalist id="seed-suggestions">
            {suggestions.map((s) => (
              <option key={s} value={s} />
            ))}
          </datalist>
        </div>
        <div>
          <label className="label">depth: {depth}</label>
          <input
            type="range"
            min={1}
            max={5}
            value={depth}
            onChange={(e) => setDepth(Number(e.target.value))}
          />
        </div>
        <button
          className="btn-primary"
          onClick={() => {
            setError(null);
            setSeed(seedInput);
          }}
          disabled={!seedInput}
        >
          탐색
        </button>
      </div>

      {error ? (
        <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {error}
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_320px]">
        <div className="card p-3">
          {sub.isError ? (
            <div className="px-2 py-6 text-center text-sm text-red-600">
              {apiErrorMessage(sub.error)}
            </div>
          ) : sub.data ? (
            <GraphCanvas
              nodes={sub.data.nodes}
              relationships={sub.data.relationships}
              onNodeClick={setSelected}
            />
          ) : seed ? (
            <div className="px-2 py-6 text-center text-sm text-slate-500">로딩 중…</div>
          ) : (
            <div className="px-2 py-12 text-center text-sm text-slate-400">
              seed를 입력하고 탐색을 실행하세요.
            </div>
          )}
        </div>

        <div className="space-y-3">
          <div className="card p-3">
            <h3 className="text-sm font-semibold">선택된 노드</h3>
            {selected ? (
              <div className="mt-2 space-y-1 text-sm">
                <div>
                  <span className="font-mono text-xs text-slate-500">
                    {selected.normalized_name}
                  </span>
                </div>
                <div>
                  <span className="badge bg-brand-50 text-brand-700">{selected.type}</span>
                  <span className="ml-2 font-medium">
                    {selected.name ?? selected.normalized_name}
                  </span>
                </div>
                {entity.data ? (
                  <div className="mt-2 space-y-2 text-xs">
                    <div className="text-slate-500">
                      DEFINED_IN: {entity.data.defined_in.length} chunk
                    </div>
                    {entity.data.defined_in.slice(0, 3).map((d) => (
                      <div
                        key={d.chunk_id}
                        className="rounded border border-slate-200 bg-slate-50 p-2"
                      >
                        <div className="font-mono text-[10px] text-slate-400">
                          {shortId(d.chunk_id)}
                        </div>
                        <div className="line-clamp-3 text-slate-700">{d.text ?? "-"}</div>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="mt-2 text-xs text-slate-500">노드를 클릭하세요.</div>
            )}
          </div>

          <div className="card p-3">
            <h3 className="text-sm font-semibold">최근 sync 로그</h3>
            <table className="mt-2 w-full text-xs">
              <thead className="text-left text-slate-500">
                <tr>
                  <th className="py-1">target</th>
                  <th className="py-1">status</th>
                  <th className="py-1">at</th>
                </tr>
              </thead>
              <tbody>
                {(syncLogs.data ?? []).map((l) => (
                  <tr key={l.id} className="border-t border-slate-100">
                    <td className="py-1">
                      {l.target_type} <span className="text-slate-400">{shortId(l.target_id)}</span>
                    </td>
                    <td className="py-1">
                      <StatusBadge status={l.sync_status} />
                    </td>
                    <td className="py-1 text-slate-500">{formatDate(l.created_at)}</td>
                  </tr>
                ))}
                {!syncLogs.data?.length ? (
                  <tr>
                    <td colSpan={3} className="py-3 text-center text-slate-400">
                      sync 로그 없음
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
