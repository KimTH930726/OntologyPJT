import { classNames } from "@/utils";

const palette: Record<string, string> = {
  PENDING: "bg-amber-100 text-amber-800",
  APPROVED: "bg-emerald-100 text-emerald-800",
  REJECTED: "bg-red-100 text-red-800",
  MERGED: "bg-slate-200 text-slate-700",
  INDEXED: "bg-emerald-100 text-emerald-800",
  FAILED: "bg-red-100 text-red-800",
  SUCCESS: "bg-emerald-100 text-emerald-800",
  SKIPPED: "bg-slate-200 text-slate-700",
};

export default function StatusBadge({ status }: { status: string }) {
  const cls = palette[status] ?? "bg-slate-100 text-slate-700";
  return <span className={classNames("badge", cls)}>{status}</span>;
}
