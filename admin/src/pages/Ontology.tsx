import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import {
  createEntityType,
  createRelationType,
  deactivateEntityType,
  deactivateRelationType,
  listEntityTypes,
  listRelationTypes,
  updateEntityType,
  updateRelationType,
} from "@/api/endpoints";
import { apiErrorMessage } from "@/api/client";
import StatusBadge from "@/components/StatusBadge";
import Modal from "@/components/Modal";
import { classNames } from "@/utils";

type Tab = "entities" | "relations";

export default function Ontology() {
  const [tab, setTab] = useState<Tab>("entities");

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Ontology Schema</h1>
        <p className="text-sm text-slate-500">
          Entity Types / Relation Types 관리. 활성화된 type만 추출에 사용됩니다.
        </p>
      </div>

      <div className="flex gap-1 border-b border-slate-200">
        {(["entities", "relations"] as Tab[]).map((t) => (
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
            {t === "entities" ? "Entity Types" : "Relation Types"}
          </button>
        ))}
      </div>

      {tab === "entities" ? <EntityTypes /> : <RelationTypes />}
      {tab === "relations" ? <RelationMatrix /> : null}
    </div>
  );
}

function EntityTypes() {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ["et-all"], queryFn: () => listEntityTypes(false) });
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", display_name: "", description: "" });
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      createEntityType({
        name: form.name,
        display_name: form.display_name,
        description: form.description || undefined,
      }),
    onSuccess: () => {
      setOpen(false);
      setForm({ name: "", display_name: "", description: "" });
      qc.invalidateQueries({ queryKey: ["et-all"] });
      qc.invalidateQueries({ queryKey: ["et"] });
    },
    onError: (e) => setError(apiErrorMessage(e)),
  });

  const toggle = useMutation({
    mutationFn: (row: { id: string; is_active: boolean }) =>
      row.is_active
        ? deactivateEntityType(row.id)
        : updateEntityType(row.id, { is_active: true }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["et-all"] });
      qc.invalidateQueries({ queryKey: ["et"] });
    },
  });

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <button className="btn-primary" onClick={() => setOpen(true)}>
          + entity type 추가
        </button>
      </div>
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="px-3 py-2">name</th>
              <th className="px-3 py-2">display</th>
              <th className="px-3 py-2">description</th>
              <th className="px-3 py-2">active</th>
              <th className="px-3 py-2">actions</th>
            </tr>
          </thead>
          <tbody>
            {(list.data ?? []).map((r) => (
              <tr key={r.id} className="border-t border-slate-100">
                <td className="px-3 py-2 font-medium">{r.name}</td>
                <td className="px-3 py-2 text-slate-600">{r.display_name}</td>
                <td className="px-3 py-2 text-slate-600">{r.description ?? "-"}</td>
                <td className="px-3 py-2">
                  <StatusBadge status={r.is_active ? "APPROVED" : "REJECTED"} />
                </td>
                <td className="px-3 py-2">
                  <button
                    className={r.is_active ? "btn-danger" : "btn-success"}
                    onClick={() => toggle.mutate({ id: r.id, is_active: r.is_active })}
                  >
                    {r.is_active ? "비활성" : "활성"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Modal
        open={open}
        title="entity type 추가"
        onClose={() => {
          setOpen(false);
          setError(null);
        }}
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
              disabled={!form.name || !form.display_name}
            >
              생성
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <div>
            <label className="label">name (코드)</label>
            <input
              className="input"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </div>
          <div>
            <label className="label">display_name</label>
            <input
              className="input"
              value={form.display_name}
              onChange={(e) => setForm({ ...form, display_name: e.target.value })}
            />
          </div>
          <div>
            <label className="label">description</label>
            <input
              className="input"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>
          {error ? <div className="text-xs text-red-600">{error}</div> : null}
        </div>
      </Modal>
    </div>
  );
}

function RelationTypes() {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ["rt-all"], queryFn: () => listRelationTypes(false) });
  const entityTypes = useQuery({ queryKey: ["et"], queryFn: () => listEntityTypes(true) });
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    source_entity_type: "",
    relation_name: "",
    target_entity_type: "",
    display_name: "",
    description: "",
  });
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      createRelationType({
        source_entity_type: form.source_entity_type,
        relation_name: form.relation_name,
        target_entity_type: form.target_entity_type,
        display_name: form.display_name,
        description: form.description || undefined,
      }),
    onSuccess: () => {
      setOpen(false);
      setForm({
        source_entity_type: "",
        relation_name: "",
        target_entity_type: "",
        display_name: "",
        description: "",
      });
      qc.invalidateQueries({ queryKey: ["rt-all"] });
      qc.invalidateQueries({ queryKey: ["rt"] });
    },
    onError: (e) => setError(apiErrorMessage(e)),
  });

  const toggle = useMutation({
    mutationFn: (row: { id: string; is_active: boolean }) =>
      row.is_active
        ? deactivateRelationType(row.id)
        : updateRelationType(row.id, { is_active: true }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["rt-all"] });
      qc.invalidateQueries({ queryKey: ["rt"] });
    },
  });

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <button className="btn-primary" onClick={() => setOpen(true)}>
          + relation type 추가
        </button>
      </div>
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="px-3 py-2">source</th>
              <th className="px-3 py-2">relation</th>
              <th className="px-3 py-2">target</th>
              <th className="px-3 py-2">display</th>
              <th className="px-3 py-2">active</th>
              <th className="px-3 py-2">actions</th>
            </tr>
          </thead>
          <tbody>
            {(list.data ?? []).map((r) => (
              <tr key={r.id} className="border-t border-slate-100">
                <td className="px-3 py-2">{r.source_entity_type}</td>
                <td className="px-3 py-2 font-mono text-xs">{r.relation_name}</td>
                <td className="px-3 py-2">{r.target_entity_type}</td>
                <td className="px-3 py-2 text-slate-600">{r.display_name}</td>
                <td className="px-3 py-2">
                  <StatusBadge status={r.is_active ? "APPROVED" : "REJECTED"} />
                </td>
                <td className="px-3 py-2">
                  <button
                    className={r.is_active ? "btn-danger" : "btn-success"}
                    onClick={() => toggle.mutate({ id: r.id, is_active: r.is_active })}
                  >
                    {r.is_active ? "비활성" : "활성"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Modal
        open={open}
        title="relation type 추가"
        onClose={() => {
          setOpen(false);
          setError(null);
        }}
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
              disabled={
                !form.source_entity_type ||
                !form.relation_name ||
                !form.target_entity_type ||
                !form.display_name
              }
            >
              생성
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="label">source</label>
              <select
                className="input"
                value={form.source_entity_type}
                onChange={(e) => setForm({ ...form, source_entity_type: e.target.value })}
              >
                <option value="">선택</option>
                {(entityTypes.data ?? []).map((t) => (
                  <option key={t.id} value={t.name}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">relation_name</label>
              <input
                className="input"
                placeholder="e.g. APPLIES_TO"
                value={form.relation_name}
                onChange={(e) => setForm({ ...form, relation_name: e.target.value })}
              />
            </div>
            <div>
              <label className="label">target</label>
              <select
                className="input"
                value={form.target_entity_type}
                onChange={(e) => setForm({ ...form, target_entity_type: e.target.value })}
              >
                <option value="">선택</option>
                {(entityTypes.data ?? []).map((t) => (
                  <option key={t.id} value={t.name}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="label">display_name</label>
            <input
              className="input"
              value={form.display_name}
              onChange={(e) => setForm({ ...form, display_name: e.target.value })}
            />
          </div>
          <div>
            <label className="label">description</label>
            <input
              className="input"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>
          {error ? <div className="text-xs text-red-600">{error}</div> : null}
        </div>
      </Modal>
    </div>
  );
}

function RelationMatrix() {
  const ents = useQuery({ queryKey: ["et"], queryFn: () => listEntityTypes(true) });
  const rels = useQuery({ queryKey: ["rt"], queryFn: () => listRelationTypes(true) });

  const cells = useMemo(() => {
    const m = new Map<string, string[]>();
    for (const r of rels.data ?? []) {
      const key = `${r.source_entity_type}::${r.target_entity_type}`;
      const arr = m.get(key) ?? [];
      arr.push(r.relation_name);
      m.set(key, arr);
    }
    return m;
  }, [rels.data]);

  if (!ents.data || !rels.data) return null;

  return (
    <div className="card mt-4 p-4">
      <h3 className="mb-3 text-sm font-semibold">허용 관계 매트릭스</h3>
      <div className="overflow-auto">
        <table className="text-xs">
          <thead>
            <tr>
              <th className="border border-slate-200 bg-slate-50 px-2 py-1 text-left">
                source ↓ / target →
              </th>
              {ents.data.map((t) => (
                <th
                  key={t.id}
                  className="border border-slate-200 bg-slate-50 px-2 py-1 text-left"
                >
                  {t.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ents.data.map((src) => (
              <tr key={src.id}>
                <th className="border border-slate-200 bg-slate-50 px-2 py-1 text-left">
                  {src.name}
                </th>
                {ents.data!.map((tgt) => {
                  const arr = cells.get(`${src.name}::${tgt.name}`) ?? [];
                  return (
                    <td
                      key={tgt.id}
                      className={classNames(
                        "border border-slate-200 px-2 py-1 align-top",
                        arr.length > 0 ? "bg-emerald-50" : "bg-white",
                      )}
                    >
                      {arr.map((n) => (
                        <div key={n} className="text-emerald-700">
                          {n}
                        </div>
                      ))}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
