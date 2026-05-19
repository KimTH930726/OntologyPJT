import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  approveEntity,
  approveRelation,
  getChunk,
  listDocuments,
  listEntityCandidates,
  listEntityTypes,
  listRelationCandidates,
  listRelationTypes,
  modifyEntity,
  modifyRelation,
  rejectEntity,
  rejectRelation,
} from "@/api/endpoints";
import type {
  ExtractedEntity,
  ExtractedRelation,
  OntologyEntityType,
  OntologyRelationType,
} from "@/api/types";
import { apiErrorMessage } from "@/api/client";
import ChunkViewer from "@/components/ChunkViewer";
import EntityCard from "@/components/EntityCard";
import RelationCard from "@/components/RelationCard";
import Modal from "@/components/Modal";
import { classNames, getReviewer, shortId } from "@/utils";

export default function Candidates() {
  const qc = useQueryClient();
  const [search, setSearch] = useSearchParams();
  const status = search.get("status") || "PENDING";
  const docId = search.get("document_id") || "";
  const chunkId = search.get("chunk_id") || "";
  const entType = search.get("entity_type") || "";
  const relType = search.get("relation_type") || "";

  const docs = useQuery({ queryKey: ["cand-docs"], queryFn: () => listDocuments({ limit: 200 }) });
  const entityTypes = useQuery({ queryKey: ["et"], queryFn: () => listEntityTypes(true) });
  const relationTypes = useQuery({ queryKey: ["rt"], queryFn: () => listRelationTypes(true) });

  const entitiesQ = useQuery({
    queryKey: ["candidates-ents", status, docId, chunkId, entType],
    queryFn: () =>
      listEntityCandidates({
        review_status: status || undefined,
        document_id: docId || undefined,
        chunk_id: chunkId || undefined,
        entity_type: entType || undefined,
        limit: 500,
      }),
  });
  const relationsQ = useQuery({
    queryKey: ["candidates-rels", status, docId, chunkId, relType],
    queryFn: () =>
      listRelationCandidates({
        review_status: status || undefined,
        document_id: docId || undefined,
        chunk_id: chunkId || undefined,
        relation_type: relType || undefined,
        limit: 500,
      }),
  });

  // entity index across all statuses for relation source/target lookup
  const allEntitiesQ = useQuery({
    queryKey: ["candidates-all-ents", docId, chunkId],
    queryFn: () =>
      listEntityCandidates({
        document_id: docId || undefined,
        chunk_id: chunkId || undefined,
        limit: 1000,
      }),
  });

  const entityIndex = useMemo(() => {
    const m = new Map<string, ExtractedEntity>();
    for (const e of allEntitiesQ.data ?? []) m.set(e.id, e);
    return m;
  }, [allEntitiesQ.data]);

  const entities = entitiesQ.data ?? [];
  const relations = relationsQ.data ?? [];

  const chunkIdsInView = useMemo(() => {
    const set = new Set<string>();
    for (const e of entities) set.add(e.chunk_id);
    for (const r of relations) set.add(r.chunk_id);
    return Array.from(set);
  }, [entities, relations]);

  const chunkQueries = useQueries({
    queries: chunkIdsInView.map((id) => ({
      queryKey: ["chunk", id],
      queryFn: () => getChunk(id),
      staleTime: 60_000,
    })),
  });
  const chunkMap = useMemo(() => {
    const m = new Map<string, string>();
    chunkQueries.forEach((q, i) => {
      if (q.data) m.set(chunkIdsInView[i], q.data.text);
    });
    return m;
  }, [chunkQueries, chunkIdsInView]);

  const [activeChunkId, setActiveChunkId] = useState<string>("");
  useEffect(() => {
    if (!activeChunkId && chunkIdsInView.length > 0) {
      setActiveChunkId(chunkIdsInView[0]);
    }
    if (activeChunkId && !chunkIdsInView.includes(activeChunkId)) {
      setActiveChunkId(chunkIdsInView[0] ?? "");
    }
  }, [chunkIdsInView, activeChunkId]);

  const filteredEntities = activeChunkId
    ? entities.filter((e) => e.chunk_id === activeChunkId)
    : entities;
  const filteredRelations = activeChunkId
    ? relations.filter((r) => r.chunk_id === activeChunkId)
    : relations;

  const [selectedEnts, setSelectedEnts] = useState<Set<string>>(new Set());
  const [selectedRels, setSelectedRels] = useState<Set<string>>(new Set());
  const [focused, setFocused] = useState<
    { kind: "entity" | "relation"; id: string } | null
  >(null);
  const [rejectTarget, setRejectTarget] = useState<
    { kind: "entity" | "relation"; id: string } | null
  >(null);
  const [rejectReason, setRejectReason] = useState("");
  const [modifyEnt, setModifyEnt] = useState<ExtractedEntity | null>(null);
  const [modifyRel, setModifyRel] = useState<ExtractedRelation | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onSuccess = () => {
    qc.invalidateQueries({ queryKey: ["candidates-ents"] });
    qc.invalidateQueries({ queryKey: ["candidates-rels"] });
    qc.invalidateQueries({ queryKey: ["candidates-all-ents"] });
  };
  const onError = (e: unknown) => setError(apiErrorMessage(e));

  const mApprE = useMutation({
    mutationFn: (id: string) => approveEntity(id, getReviewer()),
    onSuccess,
    onError,
  });
  const mRejE = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      rejectEntity(id, getReviewer(), reason),
    onSuccess,
    onError,
  });
  const mModE = useMutation({
    mutationFn: (payload: { id: string; data: Parameters<typeof modifyEntity>[1] }) =>
      modifyEntity(payload.id, payload.data),
    onSuccess,
    onError,
  });
  const mApprR = useMutation({
    mutationFn: (id: string) => approveRelation(id, getReviewer()),
    onSuccess,
    onError,
  });
  const mRejR = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      rejectRelation(id, getReviewer(), reason),
    onSuccess,
    onError,
  });
  const mModR = useMutation({
    mutationFn: (payload: { id: string; data: Parameters<typeof modifyRelation>[1] }) =>
      modifyRelation(payload.id, payload.data),
    onSuccess,
    onError,
  });

  // keyboard shortcuts
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!focused) return;
      const tag = (e.target as HTMLElement | null)?.tagName?.toLowerCase();
      if (tag === "input" || tag === "textarea") return;
      if (e.key === "a") {
        if (focused.kind === "entity") mApprE.mutate(focused.id);
        else mApprR.mutate(focused.id);
      } else if (e.key === "r") {
        setRejectTarget(focused);
        setRejectReason("");
      } else if (e.key === "m") {
        if (focused.kind === "entity") {
          const ent = entityIndex.get(focused.id);
          if (ent) setModifyEnt(ent);
        } else {
          const rel = relations.find((r) => r.id === focused.id);
          if (rel) setModifyRel(rel);
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [focused, entityIndex, relations, mApprE, mApprR]);

  const bulkApproveEntities = () => {
    for (const id of selectedEnts) mApprE.mutate(id);
    setSelectedEnts(new Set());
  };
  const bulkRejectEntities = () => {
    const reason = window.prompt("일괄 reject 사유를 입력하세요", "bulk-reject");
    if (!reason) return;
    for (const id of selectedEnts) mRejE.mutate({ id, reason });
    setSelectedEnts(new Set());
  };
  const bulkApproveRelations = () => {
    for (const id of selectedRels) mApprR.mutate(id);
    setSelectedRels(new Set());
  };
  const bulkRejectRelations = () => {
    const reason = window.prompt("일괄 reject 사유를 입력하세요", "bulk-reject");
    if (!reason) return;
    for (const id of selectedRels) mRejR.mutate({ id, reason });
    setSelectedRels(new Set());
  };

  const highlights = filteredEntities.map((e) => e.name);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label className="label">status</label>
          <select
            className="input w-36"
            value={status}
            onChange={(e) => setParam(setSearch, "status", e.target.value)}
          >
            {["PENDING", "APPROVED", "REJECTED", "MERGED", ""].map((s) => (
              <option key={s} value={s}>
                {s || "(전체)"}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">document</label>
          <select
            className="input w-72"
            value={docId}
            onChange={(e) => setParam(setSearch, "document_id", e.target.value)}
          >
            <option value="">(전체)</option>
            {(docs.data ?? []).map((d) => (
              <option key={d.id} value={d.id}>
                {d.title} ({shortId(d.id)})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">entity type</label>
          <select
            className="input w-44"
            value={entType}
            onChange={(e) => setParam(setSearch, "entity_type", e.target.value)}
          >
            <option value="">(전체)</option>
            {(entityTypes.data ?? []).map((t) => (
              <option key={t.id} value={t.name}>
                {t.display_name} ({t.name})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">relation type</label>
          <select
            className="input w-48"
            value={relType}
            onChange={(e) => setParam(setSearch, "relation_type", e.target.value)}
          >
            <option value="">(전체)</option>
            {(relationTypes.data ?? []).map((t) => (
              <option key={t.id} value={t.relation_name}>
                {t.display_name} ({t.relation_name})
              </option>
            ))}
          </select>
        </div>
        {chunkId ? (
          <div className="text-xs text-slate-500">
            chunk_id 필터 활성:
            <span className="ml-1 font-mono">{shortId(chunkId)}</span>
            <button
              className="ml-2 text-brand-600 hover:underline"
              onClick={() => setParam(setSearch, "chunk_id", "")}
            >
              해제
            </button>
          </div>
        ) : null}
        <div className="ml-auto text-xs text-slate-500">
          단축키: <kbd>a</kbd> approve · <kbd>r</kbd> reject · <kbd>m</kbd> modify
        </div>
      </div>

      {error ? (
        <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {error}
          <button className="ml-2 underline" onClick={() => setError(null)}>
            닫기
          </button>
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">
              Chunks ({chunkIdsInView.length})
            </h2>
            {activeChunkId ? (
              <div className="font-mono text-xs text-slate-400">{activeChunkId}</div>
            ) : null}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {chunkIdsInView.map((cid) => (
              <button
                key={cid}
                onClick={() => setActiveChunkId(cid)}
                className={classNames(
                  "rounded border px-2 py-0.5 text-xs",
                  activeChunkId === cid
                    ? "border-brand-500 bg-brand-50 text-brand-700"
                    : "border-slate-300 bg-white text-slate-600 hover:bg-slate-50",
                )}
              >
                {shortId(cid)}
              </button>
            ))}
          </div>
          {activeChunkId ? (
            <ChunkViewer
              text={chunkMap.get(activeChunkId) ?? "(loading)"}
              highlights={highlights}
            />
          ) : (
            <div className="text-sm text-slate-500">
              표시할 후보가 없습니다.
            </div>
          )}
        </div>

        <div className="space-y-4">
          <Section
            title={`Entities (${filteredEntities.length})`}
            bulk={
              selectedEnts.size > 0 ? (
                <>
                  <button className="btn-success" onClick={bulkApproveEntities}>
                    선택 {selectedEnts.size} approve
                  </button>
                  <button className="btn-danger" onClick={bulkRejectEntities}>
                    선택 {selectedEnts.size} reject
                  </button>
                </>
              ) : null
            }
          >
            <div className="space-y-2">
              {filteredEntities.map((e) => (
                <div key={e.id} onMouseEnter={() => setFocused({ kind: "entity", id: e.id })}>
                  <EntityCard
                    entity={e}
                    selected={selectedEnts.has(e.id)}
                    onSelect={(checked) => {
                      const next = new Set(selectedEnts);
                      checked ? next.add(e.id) : next.delete(e.id);
                      setSelectedEnts(next);
                    }}
                    onApprove={() => mApprE.mutate(e.id)}
                    onReject={() => {
                      setRejectTarget({ kind: "entity", id: e.id });
                      setRejectReason("");
                    }}
                    onModify={() => setModifyEnt(e)}
                    busy={mApprE.isPending || mRejE.isPending}
                  />
                </div>
              ))}
              {filteredEntities.length === 0 ? (
                <div className="text-xs text-slate-400">표시할 entity가 없습니다.</div>
              ) : null}
            </div>
          </Section>

          <Section
            title={`Relations (${filteredRelations.length})`}
            bulk={
              selectedRels.size > 0 ? (
                <>
                  <button className="btn-success" onClick={bulkApproveRelations}>
                    선택 {selectedRels.size} approve
                  </button>
                  <button className="btn-danger" onClick={bulkRejectRelations}>
                    선택 {selectedRels.size} reject
                  </button>
                </>
              ) : null
            }
          >
            <div className="space-y-2">
              {filteredRelations.map((r) => (
                <div key={r.id} onMouseEnter={() => setFocused({ kind: "relation", id: r.id })}>
                  <RelationCard
                    relation={r}
                    entityIndex={entityIndex}
                    selected={selectedRels.has(r.id)}
                    onSelect={(checked) => {
                      const next = new Set(selectedRels);
                      checked ? next.add(r.id) : next.delete(r.id);
                      setSelectedRels(next);
                    }}
                    onApprove={() => mApprR.mutate(r.id)}
                    onReject={() => {
                      setRejectTarget({ kind: "relation", id: r.id });
                      setRejectReason("");
                    }}
                    onModify={() => setModifyRel(r)}
                    busy={mApprR.isPending || mRejR.isPending}
                  />
                </div>
              ))}
              {filteredRelations.length === 0 ? (
                <div className="text-xs text-slate-400">표시할 relation이 없습니다.</div>
              ) : null}
            </div>
          </Section>
        </div>
      </div>

      <Modal
        open={!!rejectTarget}
        title="reject 사유"
        onClose={() => setRejectTarget(null)}
        footer={
          <>
            <button className="btn-ghost" onClick={() => setRejectTarget(null)}>
              취소
            </button>
            <button
              className="btn-danger"
              onClick={() => {
                if (!rejectTarget || !rejectReason) return;
                if (rejectTarget.kind === "entity")
                  mRejE.mutate({ id: rejectTarget.id, reason: rejectReason });
                else mRejR.mutate({ id: rejectTarget.id, reason: rejectReason });
                setRejectTarget(null);
              }}
              disabled={!rejectReason}
            >
              reject
            </button>
          </>
        }
      >
        <label className="label">사유</label>
        <input
          className="input"
          autoFocus
          value={rejectReason}
          onChange={(e) => setRejectReason(e.target.value)}
        />
      </Modal>

      <ModifyEntityModal
        target={modifyEnt}
        onClose={() => setModifyEnt(null)}
        types={entityTypes.data ?? []}
        onSubmit={(data) => {
          if (!modifyEnt) return;
          mModE.mutate(
            { id: modifyEnt.id, data: { reviewer: getReviewer(), ...data } },
            { onSuccess: () => setModifyEnt(null) },
          );
        }}
      />

      <ModifyRelationModal
        target={modifyRel}
        onClose={() => setModifyRel(null)}
        types={relationTypes.data ?? []}
        onSubmit={(data) => {
          if (!modifyRel) return;
          mModR.mutate(
            { id: modifyRel.id, data: { reviewer: getReviewer(), ...data } },
            { onSuccess: () => setModifyRel(null) },
          );
        }}
      />
    </div>
  );
}

function setParam(setSearch: ReturnType<typeof useSearchParams>[1], k: string, v: string) {
  setSearch((prev) => {
    const next = new URLSearchParams(prev);
    if (v) next.set(k, v);
    else next.delete(k);
    return next;
  });
}

function Section({
  title,
  bulk,
  children,
}: {
  title: string;
  bulk?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="card p-3">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
        <div className="flex gap-2">{bulk}</div>
      </div>
      {children}
    </div>
  );
}

function ModifyEntityModal({
  target,
  onClose,
  onSubmit,
  types,
}: {
  target: ExtractedEntity | null;
  onClose: () => void;
  onSubmit: (data: { name?: string; normalized_name?: string; entity_type?: string }) => void;
  types: OntologyEntityType[];
}) {
  const [name, setName] = useState("");
  const [normName, setNormName] = useState("");
  const [etype, setEtype] = useState("");

  useEffect(() => {
    if (target) {
      setName(target.name);
      setNormName(target.normalized_name);
      setEtype(target.entity_type);
    }
  }, [target]);

  return (
    <Modal
      open={!!target}
      title="entity 수정"
      onClose={onClose}
      footer={
        <>
          <button className="btn-ghost" onClick={onClose}>
            취소
          </button>
          <button
            className="btn-primary"
            onClick={() =>
              onSubmit({
                name: name !== target?.name ? name : undefined,
                normalized_name: normName !== target?.normalized_name ? normName : undefined,
                entity_type: etype !== target?.entity_type ? etype : undefined,
              })
            }
          >
            저장
          </button>
        </>
      }
    >
      <div className="space-y-3">
        <div>
          <label className="label">name</label>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <label className="label">normalized_name</label>
          <input
            className="input"
            value={normName}
            onChange={(e) => setNormName(e.target.value)}
          />
        </div>
        <div>
          <label className="label">entity_type</label>
          <select className="input" value={etype} onChange={(e) => setEtype(e.target.value)}>
            {types.map((t) => (
              <option key={t.id} value={t.name}>
                {t.display_name} ({t.name})
              </option>
            ))}
          </select>
        </div>
      </div>
    </Modal>
  );
}

function ModifyRelationModal({
  target,
  onClose,
  onSubmit,
  types,
}: {
  target: ExtractedRelation | null;
  onClose: () => void;
  onSubmit: (data: {
    relation_type?: string;
    source_entity_name?: string;
    source_entity_type?: string;
    target_entity_name?: string;
    target_entity_type?: string;
  }) => void;
  types: OntologyRelationType[];
}) {
  const [relName, setRelName] = useState("");
  const [srcName, setSrcName] = useState("");
  const [tgtName, setTgtName] = useState("");

  useEffect(() => {
    if (target) {
      setRelName(target.relation_type);
      setSrcName(target.source_entity_name);
      setTgtName(target.target_entity_name);
    }
  }, [target]);

  return (
    <Modal
      open={!!target}
      title="relation 수정"
      onClose={onClose}
      footer={
        <>
          <button className="btn-ghost" onClick={onClose}>
            취소
          </button>
          <button
            className="btn-primary"
            onClick={() =>
              onSubmit({
                relation_type: relName !== target?.relation_type ? relName : undefined,
                source_entity_name:
                  srcName !== target?.source_entity_name ? srcName : undefined,
                target_entity_name:
                  tgtName !== target?.target_entity_name ? tgtName : undefined,
              })
            }
          >
            저장
          </button>
        </>
      }
    >
      <div className="space-y-3">
        <div>
          <label className="label">relation_type</label>
          <select
            className="input"
            value={relName}
            onChange={(e) => setRelName(e.target.value)}
          >
            {types.map((t) => (
              <option key={t.id} value={t.relation_name}>
                {t.display_name} ({t.source_entity_type} -[{t.relation_name}]→{" "}
                {t.target_entity_type})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">source name</label>
          <input className="input" value={srcName} onChange={(e) => setSrcName(e.target.value)} />
        </div>
        <div>
          <label className="label">target name</label>
          <input className="input" value={tgtName} onChange={(e) => setTgtName(e.target.value)} />
        </div>
      </div>
    </Modal>
  );
}
