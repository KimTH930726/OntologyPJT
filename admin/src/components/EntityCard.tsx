import { ExtractedEntity } from "@/api/types";
import StatusBadge from "./StatusBadge";
import { classNames } from "@/utils";

export default function EntityCard({
  entity,
  selected,
  onSelect,
  onApprove,
  onReject,
  onModify,
  busy,
}: {
  entity: ExtractedEntity;
  selected?: boolean;
  onSelect?: (checked: boolean) => void;
  onApprove?: () => void;
  onReject?: () => void;
  onModify?: () => void;
  busy?: boolean;
}) {
  const conf = Number(entity.confidence);
  return (
    <div
      className={classNames(
        "card p-3",
        selected && "ring-2 ring-brand-400",
        entity.review_status === "REJECTED" && "opacity-60",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            {onSelect ? (
              <input
                type="checkbox"
                checked={!!selected}
                onChange={(e) => onSelect(e.target.checked)}
              />
            ) : null}
            <div className="truncate font-semibold text-slate-900">{entity.name}</div>
            <span className="badge bg-brand-50 text-brand-700">{entity.entity_type}</span>
            <StatusBadge status={entity.review_status} />
          </div>
          <div className="mt-0.5 truncate text-xs text-slate-500">
            norm: {entity.normalized_name} · conf: {Number.isFinite(conf) ? conf.toFixed(2) : "-"}
          </div>
        </div>
      </div>
      {entity.evidence_text ? (
        <div className="mt-2 line-clamp-2 text-xs text-slate-600">
          “{entity.evidence_text}”
        </div>
      ) : null}
      {entity.rejection_reason ? (
        <div className="mt-1 text-xs text-red-600">reason: {entity.rejection_reason}</div>
      ) : null}
      {entity.review_status === "PENDING" ? (
        <div className="mt-3 flex gap-2">
          <button className="btn-success" onClick={onApprove} disabled={busy}>
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
