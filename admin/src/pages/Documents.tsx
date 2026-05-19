import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useState } from "react";
import {
  createDocument,
  extractDocument,
  listDocuments,
  listEntityCandidates,
  listRelationCandidates,
} from "@/api/endpoints";
import { apiErrorMessage } from "@/api/client";
import Modal from "@/components/Modal";
import { formatDate, shortId } from "@/utils";

function CountsCell({ documentId }: { documentId: string }) {
  const ents = useQuery({
    queryKey: ["doc-ent-counts", documentId],
    queryFn: () => listEntityCandidates({ document_id: documentId, limit: 500 }),
  });
  const rels = useQuery({
    queryKey: ["doc-rel-counts", documentId],
    queryFn: () => listRelationCandidates({ document_id: documentId, limit: 500 }),
  });
  if (ents.isLoading || rels.isLoading) return <span className="text-xs text-slate-400">…</span>;
  const e = ents.data ?? [];
  const r = rels.data ?? [];
  const pe = e.filter((x) => x.review_status === "PENDING").length;
  const ae = e.filter((x) => x.review_status === "APPROVED").length;
  const pr = r.filter((x) => x.review_status === "PENDING").length;
  const ar = r.filter((x) => x.review_status === "APPROVED").length;
  return (
    <span className="text-xs">
      <span className="text-amber-700">{pe + pr}P</span>{" "}
      <span className="text-emerald-700">{ae + ar}A</span>{" "}
      <span className="text-slate-400">/ {e.length + r.length}</span>
    </span>
  );
}

export default function Documents() {
  const qc = useQueryClient();
  const [domain, setDomain] = useState("");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    title: "",
    domain: "ecommerce",
    content: "",
    version: "v1",
    access_level: "internal",
  });
  const [error, setError] = useState<string | null>(null);

  const docs = useQuery({
    queryKey: ["documents", domain],
    queryFn: () => listDocuments({ domain: domain || undefined, limit: 200 }),
  });

  const create = useMutation({
    mutationFn: () => createDocument(form),
    onSuccess: () => {
      setOpen(false);
      setForm({ ...form, title: "", content: "" });
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (e) => setError(apiErrorMessage(e)),
  });

  const extract = useMutation({
    mutationFn: (id: string) => extractDocument(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["documents"] });
      qc.invalidateQueries({ queryKey: ["doc-ent-counts"] });
      qc.invalidateQueries({ queryKey: ["doc-rel-counts"] });
    },
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">문서</h1>
          <p className="text-sm text-slate-500">원문 업로드 / 재추출 / 삭제.</p>
        </div>
        <button className="btn-primary" onClick={() => setOpen(true)}>
          + 문서 업로드
        </button>
      </div>

      <div className="card flex items-end gap-3 p-3">
        <div className="w-64">
          <label className="label">domain 필터</label>
          <input
            className="input"
            value={domain}
            placeholder="ecommerce"
            onChange={(e) => setDomain(e.target.value)}
          />
        </div>
        <button
          className="btn-ghost"
          onClick={() => qc.invalidateQueries({ queryKey: ["documents"] })}
        >
          새로고침
        </button>
      </div>

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="px-3 py-2">id</th>
              <th className="px-3 py-2">title</th>
              <th className="px-3 py-2">domain</th>
              <th className="px-3 py-2">version</th>
              <th className="px-3 py-2">candidates</th>
              <th className="px-3 py-2">uploaded</th>
              <th className="px-3 py-2">actions</th>
            </tr>
          </thead>
          <tbody>
            {(docs.data ?? []).map((d) => (
              <tr key={d.id} className="border-t border-slate-100">
                <td className="px-3 py-2 font-mono text-xs text-slate-400">
                  {shortId(d.id)}
                </td>
                <td className="px-3 py-2">
                  <Link to={`/documents/${d.id}`} className="text-brand-700 hover:underline">
                    {d.title}
                  </Link>
                </td>
                <td className="px-3 py-2 text-slate-600">{d.domain}</td>
                <td className="px-3 py-2 text-slate-600">{d.version}</td>
                <td className="px-3 py-2"><CountsCell documentId={d.id} /></td>
                <td className="px-3 py-2 text-slate-500">{formatDate(d.created_at)}</td>
                <td className="px-3 py-2">
                  <button
                    className="btn-ghost"
                    onClick={() => extract.mutate(d.id)}
                    disabled={extract.isPending && extract.variables === d.id}
                  >
                    재추출
                  </button>
                </td>
              </tr>
            ))}
            {!docs.data?.length && !docs.isLoading ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-sm text-slate-400">
                  문서가 없습니다. 우측 상단에서 업로드 하세요.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <Modal
        open={open}
        onClose={() => {
          setOpen(false);
          setError(null);
        }}
        title="문서 업로드"
        footer={
          <>
            <button className="btn-ghost" onClick={() => setOpen(false)}>
              취소
            </button>
            <button
              className="btn-primary"
              onClick={() => {
                setError(null);
                create.mutate();
              }}
              disabled={!form.title || !form.content || create.isPending}
            >
              {create.isPending ? "업로드 중…" : "업로드"}
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <div>
            <label className="label">title</label>
            <input
              className="input"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="label">domain</label>
              <input
                className="input"
                value={form.domain}
                onChange={(e) => setForm({ ...form, domain: e.target.value })}
              />
            </div>
            <div>
              <label className="label">version</label>
              <input
                className="input"
                value={form.version}
                onChange={(e) => setForm({ ...form, version: e.target.value })}
              />
            </div>
            <div>
              <label className="label">access_level</label>
              <input
                className="input"
                value={form.access_level}
                onChange={(e) => setForm({ ...form, access_level: e.target.value })}
              />
            </div>
          </div>
          <div>
            <label className="label">content</label>
            <textarea
              className="input h-48 font-mono text-xs"
              value={form.content}
              onChange={(e) => setForm({ ...form, content: e.target.value })}
            />
          </div>
          {error ? <div className="text-xs text-red-600">{error}</div> : null}
        </div>
      </Modal>
    </div>
  );
}
