import { ExtractedEntity, ExtractedRelation } from "@/api/types";
import StatusBadge from "./StatusBadge";
import { classNames } from "@/utils";

export default function RelationCard({
  relation,
  entityIndex,
  selected,
  onSelect,
  onApprove,
  onReject,
  onModify,
  busy,
}: {
  relation: ExtractedRelation;
  entityIndex: Map<string, ExtractedEntity>;
  selected?: boolean;
  onSelect?: (checked: boolean) => void;
  onApprove?: () => void;
  onReject?: () => void;
  onModify?: () => void;
  busy?: boolean;
}) {
  const src = relation.source_entity_id
    ? entityIndex.get(relation.source_entity_id)
    : undefined;
  const tgt = relation.target_entity_id
    ? entityIndex.get(relation.target_entity_id)
    : undefined;
  const srcApproved = src?.review_status === "APPROVED";
  const tgtApproved = tgt?.review_status === "APPROVED";
  const canApprove =
    relation.review_status === "PENDING" && srcApproved && tgtApproved;
  const isSchemaViolation =
    relation.review_status === "REJECTED" &&
    (relation.rejection_reason ?? "").toUpperCase().includes("SCHEMA");
  const conf = Number(relation.confidence);

  return (
    <div
      className={classNames(
        "card p-3",
        selected && "ring-2 ring-brand-400",
        isSchemaViolation && "border-slate-300 bg-slate-50 opacity-70",
        relation.review_status === "PENDING" &&
          (!srcApproved || !tgtApproved) &&
          "border-red-300",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            {onSelect ? (
              <input
                type="checkbox"
                checked={!!selected}
                onChange={(e) => onSelect(e.target.checked)}
              />
            ) : null}
            <span className="badge bg-brand-50 text-brand-700">
              {relation.relation_type}
            </span>
            <StatusBadge status={relation.review_status} />
            {isSchemaViolation ? (
              <span className="badge bg-slate-300 text-slate-700">SCHEMA</span>
            ) : null}
          </div>
          <div className="mt-1 text-sm">
            <span
              className={classNames(
                "font-medium",
                srcApproved ? "text-emerald-700" : "text-slate-700",
              )}
            >
              {relation.source_entity_name}
            </span>
            <span className="mx-2 text-slate-400">
              ({relation.source_entity_type})
            </span>
            <span className="text-slate-500">→</span>
            <span
              className={classNames(
                "ml-2 font-medium",
                tgtApproved ? "text-emerald-700" : "text-slate-700",
              )}
            >
              {relation.target_entity_name}
            </span>
            <span className="ml-2 text-slate-400">
              ({relation.target_entity_type})
            </span>
          </div>
          <div className="text-xs text-slate-500">
            conf: {Number.isFinite(conf) ? conf.toFixed(2) : "-"}
            {!srcApproved || !tgtApproved ? (
              <span className="ml-2 text-red-600">
                · 양쪽 entity가 APPROVED여야 approve 가능
              </span>
            ) : null}
          </div>
        </div>
      </div>
      {relation.evidence_text ? (
        <div className="mt-2 line-clamp-2 text-xs text-slate-600">
          “{relation.evidence_text}”
        </div>
      ) : null}
      {relation.rejection_reason ? (
        <div className="mt-1 text-xs text-red-600">
          reason: {relation.rejection_reason}
        </div>
      ) : null}
      {relation.review_status === "PENDING" ? (
        <div className="mt-3 flex gap-2">
          <button
            className="btn-success"
            onClick={onApprove}
            disabled={!canApprove || busy}
            title={
              canApprove
                ? "approve relation"
                : "양쪽 entity가 APPROVED여야 approve 가능"
            }
          >
            <kbd className="mr-1 text-[10px]">a</kbd>approve
          </button>
          <button className="btn-danger" onClick={onReject} disabled={busy}>
            <kbd className="mr-1 text-[10px]">r</kbd>reject
          </button>
          <button className="btn-ghost" onClick={onModify} disabled={busy}>
            <kbd className="mr-1 text-[10px]">m</kbd>modify
          </button>
        </div>
      ) : null}
    </div>
  );
}
