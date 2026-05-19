import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useState } from "react";
import {
  extractChunk,
  extractDocument,
  getDocument,
  listAuditLogs,
  listDocumentChunks,
  listEntityCandidates,
  listRelationCandidates,
} from "@/api/endpoints";
import StatusBadge from "@/components/StatusBadge";
import { formatDate, shortId } from "@/utils";
import { classNames } from "@/utils";

type Tab = "chunks" | "extraction" | "audit";

export default function DocumentDetail() {
  const { id = "" } = useParams();
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("chunks");
  const [selectedChunk, setSelectedChunk] = useState<string | null>(null);

  const doc = useQuery({ queryKey: ["doc", id], queryFn: () => getDocument(id), enabled: !!id });
  const chunks = useQuery({
    queryKey: ["doc-chunks", id],
    queryFn: () => listDocumentChunks(id),
    enabled: !!id,
  });
  const ents = useQuery({
    queryKey: ["doc-ents", id],
    queryFn: () => listEntityCandidates({ document_id: id, limit: 500 }),
    enabled: !!id,
  });
  const rels = useQuery({
    queryKey: ["doc-rels", id],
    queryFn: () => listRelationCandidates({ document_id: id, limit: 500 }),
    enabled: !!id,
  });
  const audit = useQuery({
    queryKey: ["doc-audit", id],
    queryFn: () => listAuditLogs({ document_id: id, limit: 100 }),
    enabled: !!id && tab === "audit",
  });

  const extract = useMutation({
    mutationFn: () => extractDocument(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["doc", id] });
      qc.invalidateQueries({ queryKey: ["doc-chunks", id] });
      qc.invalidateQueries({ queryKey: ["doc-ents", id] });
      qc.invalidateQueries({ queryKey: ["doc-rels", id] });
    },
  });

  const extractOne = useMutation({
    mutationFn: (chunkId: string) => extractChunk(chunkId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["doc-ents", id] });
      qc.invalidateQueries({ queryKey: ["doc-rels", id] });
    },
  });

  if (doc.isLoading) return <div className="text-sm text-slate-500">로딩 중…</div>;
  if (!doc.data)
    return <div className="text-sm text-red-600">문서를 찾을 수 없습니다.</div>;

  const d = doc.data;
  const chunk = chunks.data?.find((c) => c.id === selectedChunk) ?? chunks.data?.[0];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs text-slate-500">
            <Link to="/documents" className="hover:underline">
              ← 문서 목록
            </Link>
          </div>
          <h1 className="text-xl font-bold text-slate-900">{d.title}</h1>
          <div className="mt-1 text-xs text-slate-500">
            <span className="font-mono">{shortId(d.id)}</span> · domain={d.domain} ·
            version={d.version} · access={d.access_level} · chunks=
            {d.chunk_count} · vector=<StatusBadge status={d.vector_status} />
          </div>
        </div>
        <div className="flex gap-2">
          <button
            className="btn-ghost"
            onClick={() => extract.mutate()}
            disabled={extract.isPending}
          >
            문서 재추출
          </button>
          <Link
            to={`/candidates?document_id=${d.id}`}
            className="btn-primary"
          >
            이 문서 검수하러 가기
          </Link>
        </div>
      </div>

      <div className="flex gap-1 border-b border-slate-200">
        {(["chunks", "extraction", "audit"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={classNames(
              "border-b-2 px-3 py-1.5 text-sm",
              tab === t
                ? "border-brand-600 font-semibold text-brand-700"
                : "border-transparent text-slate-500 hover:text-slate-700",
            )}
          >
            {t === "chunks" ? "Chunks" : t === "extraction" ? "Extraction Status" : "Audit"}
          </button>
        ))}
      </div>

      {tab === "chunks" ? (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[280px_1fr]">
          <div className="card max-h-[70vh] overflow-auto">
            <div className="border-b border-slate-100 px-3 py-2 text-xs font-semibold text-slate-500">
              Chunks ({chunks.data?.length ?? 0})
            </div>
            <ul>
              {(chunks.data ?? []).map((c) => (
                <li
                  key={c.id}
                  className={classNames(
                    "cursor-pointer border-b border-slate-100 px-3 py-2 text-sm hover:bg-slate-50",
                    (chunk?.id ?? "") === c.id && "bg-brand-50",
                  )}
                  onClick={() => setSelectedChunk(c.id)}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium">seq #{c.chunk_index}</span>
                    <StatusBadge status={c.vector_status} />
                  </div>
                  <div className="text-xs text-slate-500">
                    {c.token_count} tokens · {shortId(c.id)}
                  </div>
                </li>
              ))}
            </ul>
          </div>
          <div className="space-y-3">
            {chunk ? (
              <>
                <div className="flex items-center justify-between">
                  <div className="text-xs text-slate-500 font-mono">{chunk.id}</div>
                  <div className="flex gap-2">
                    <button
                      className="btn-ghost"
                      onClick={() => extractOne.mutate(chunk.id)}
                      disabled={extractOne.isPending && extractOne.variables === chunk.id}
                    >
                      이 chunk 재추출
                    </button>
                    <Link
                      to={`/candidates?chunk_id=${chunk.id}`}
                      className="btn-primary"
                    >
                      이 chunk 검수
                    </Link>
                  </div>
                </div>
                <div className="card whitespace-pre-wrap p-4 text-sm leading-7 text-slate-800">
                  {chunk.text}
                </div>
              </>
            ) : (
              <div className="text-sm text-slate-500">chunk가 없습니다.</div>
            )}
          </div>
        </div>
      ) : null}

      {tab === "extraction" ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="card p-4">
            <h3 className="text-sm font-semibold">Entities</h3>
            <SummaryByStatus rows={(ents.data ?? []).map((e) => e.review_status)} />
          </div>
          <div className="card p-4">
            <h3 className="text-sm font-semibold">Relations</h3>
            <SummaryByStatus rows={(rels.data ?? []).map((r) => r.review_status)} />
          </div>
        </div>
      ) : null}

      {tab === "audit" ? (
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
              {(audit.data ?? []).map((a) => (
                <tr key={a.id} className="border-t border-slate-100">
                  <td className="px-3 py-2"><StatusBadge status={a.action} /></td>
                  <td className="px-3 py-2">
                    {a.target_type ?? "-"}{" "}
                    <span className="font-mono text-xs text-slate-400">{shortId(a.target_id)}</span>
                  </td>
                  <td className="px-3 py-2">{a.actor ?? "-"}</td>
                  <td className="px-3 py-2 text-slate-500">{formatDate(a.created_at)}</td>
                </tr>
              ))}
              {!audit.data?.length && !audit.isLoading ? (
                <tr>
                  <td colSpan={4} className="py-6 text-center text-xs text-slate-400">
                    audit 기록 없음
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}

function SummaryByStatus({ rows }: { rows: string[] }) {
  const counts: Record<string, number> = {};
  for (const r of rows) counts[r] = (counts[r] || 0) + 1;
  const keys = ["PENDING", "APPROVED", "REJECTED", "MERGED"];
  return (
    <div className="mt-2 flex flex-wrap gap-3 text-sm">
      {keys.map((k) => (
        <div key={k} className="flex items-center gap-2">
          <StatusBadge status={k} />
          <span className="font-semibold">{counts[k] ?? 0}</span>
        </div>
      ))}
      <div className="ml-auto text-xs text-slate-500">total: {rows.length}</div>
    </div>
  );
}
