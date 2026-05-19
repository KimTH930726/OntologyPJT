import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  listAuditLogs,
  listDocuments,
  listEntityCandidates,
  listQaLogs,
  listRelationCandidates,
} from "@/api/endpoints";
import { formatDate, shortId } from "@/utils";
import StatusBadge from "@/components/StatusBadge";

function Stat({
  label,
  value,
  to,
  hint,
}: {
  label: string;
  value: number | string;
  to?: string;
  hint?: string;
}) {
  const body = (
    <div className="card flex h-full flex-col justify-between p-4 transition hover:border-brand-300">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="mt-1 text-3xl font-bold text-slate-900">{value}</div>
      {hint ? <div className="mt-1 text-xs text-slate-500">{hint}</div> : null}
    </div>
  );
  return to ? <Link to={to}>{body}</Link> : body;
}

export default function Dashboard() {
  const docs = useQuery({ queryKey: ["dash-docs"], queryFn: () => listDocuments({ limit: 100 }) });
  const pendingEntities = useQuery({
    queryKey: ["dash-pending-ent"],
    queryFn: () => listEntityCandidates({ review_status: "PENDING", limit: 500 }),
  });
  const approvedEntities = useQuery({
    queryKey: ["dash-approved-ent"],
    queryFn: () => listEntityCandidates({ review_status: "APPROVED", limit: 500 }),
  });
  const pendingRelations = useQuery({
    queryKey: ["dash-pending-rel"],
    queryFn: () => listRelationCandidates({ review_status: "PENDING", limit: 500 }),
  });
  const approvedRelations = useQuery({
    queryKey: ["dash-approved-rel"],
    queryFn: () => listRelationCandidates({ review_status: "APPROVED", limit: 500 }),
  });
  const recentQa = useQuery({ queryKey: ["dash-qa"], queryFn: () => listQaLogs({ limit: 5 }) });
  const recentAudit = useQuery({
    queryKey: ["dash-audit"],
    queryFn: () => listAuditLogs({ limit: 5 }),
  });

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const queriesToday = (recentQa.data ?? []).filter(
    (q) => new Date(q.created_at).getTime() >= today.getTime(),
  ).length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900">대시보드</h1>
        <p className="text-sm text-slate-500">
          전체 검수/거버넌스 현황 한눈 보기.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
        <Stat label="문서" value={docs.data?.length ?? "…"} to="/documents" />
        <Stat
          label="Pending Entities"
          value={pendingEntities.data?.length ?? "…"}
          to="/candidates?status=PENDING&type=entity"
        />
        <Stat
          label="Pending Relations"
          value={pendingRelations.data?.length ?? "…"}
          to="/candidates?status=PENDING&type=relation"
        />
        <Stat
          label="Approved Entities"
          value={approvedEntities.data?.length ?? "…"}
        />
        <Stat
          label="Approved Relations"
          value={approvedRelations.data?.length ?? "…"}
        />
        <Stat label="Queries (5 recent)" value={queriesToday + "/" + (recentQa.data?.length ?? 0)} to="/qa" hint="오늘 / 최근 5건" />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="card p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">최근 문서</h2>
            <Link to="/documents" className="text-xs text-brand-600 hover:underline">
              전체 보기
            </Link>
          </div>
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-slate-500">
              <tr>
                <th className="py-1">title</th>
                <th className="py-1">domain</th>
                <th className="py-1">version</th>
                <th className="py-1">uploaded</th>
              </tr>
            </thead>
            <tbody>
              {(docs.data ?? []).slice(0, 8).map((d) => (
                <tr key={d.id} className="border-t border-slate-100">
                  <td className="py-1.5">
                    <Link to={`/documents/${d.id}`} className="text-brand-700 hover:underline">
                      {d.title}
                    </Link>
                  </td>
                  <td className="text-slate-600">{d.domain}</td>
                  <td className="text-slate-600">{d.version}</td>
                  <td className="text-slate-500">{formatDate(d.created_at)}</td>
                </tr>
              ))}
              {!docs.data?.length && !docs.isLoading ? (
                <tr>
                  <td colSpan={4} className="py-6 text-center text-xs text-slate-400">
                    문서가 없습니다
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>

        <div className="card p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">최근 Audit</h2>
            <Link to="/audit" className="text-xs text-brand-600 hover:underline">
              전체 보기
            </Link>
          </div>
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-slate-500">
              <tr>
                <th className="py-1">action</th>
                <th className="py-1">target</th>
                <th className="py-1">actor</th>
                <th className="py-1">at</th>
              </tr>
            </thead>
            <tbody>
              {(recentAudit.data ?? []).map((a) => (
                <tr key={a.id} className="border-t border-slate-100">
                  <td className="py-1.5"><StatusBadge status={a.action} /></td>
                  <td className="text-slate-600">
                    {a.target_type ? `${a.target_type}` : "-"}{" "}
                    <span className="font-mono text-xs text-slate-400">
                      {shortId(a.target_id)}
                    </span>
                  </td>
                  <td className="text-slate-600">{a.actor || "-"}</td>
                  <td className="text-slate-500">{formatDate(a.created_at)}</td>
                </tr>
              ))}
              {!recentAudit.data?.length && !recentAudit.isLoading ? (
                <tr>
                  <td colSpan={4} className="py-6 text-center text-xs text-slate-400">
                    audit 기록 없음
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
