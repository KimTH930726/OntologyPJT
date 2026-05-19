import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ask, getQaLog, listQaLogs } from "@/api/endpoints";
import { apiErrorMessage } from "@/api/client";
import JsonViewer from "@/components/JsonViewer";
import { formatDate, shortId } from "@/utils";
import type { QAResponse } from "@/api/types";

export default function QA() {
  const [question, setQuestion] = useState(
    "주문 O1001은 환불 가능한가?",
  );
  const [resp, setResp] = useState<QAResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedLog, setSelectedLog] = useState<string | null>(null);

  const run = useMutation({
    mutationFn: () => ask(question),
    onSuccess: (data) => {
      setResp(data);
      setSelectedLog(data.query_log_id);
      logs.refetch();
    },
    onError: (e) => {
      setError(apiErrorMessage(e));
      setResp(null);
    },
  });

  const logs = useQuery({
    queryKey: ["qa-logs"],
    queryFn: () => listQaLogs({ limit: 20 }),
  });

  const detail = useQuery({
    queryKey: ["qa-log", selectedLog],
    queryFn: () => getQaLog(selectedLog!),
    enabled: !!selectedLog,
  });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">질의 테스트</h1>
        <p className="text-sm text-slate-500">
          GraphRAG: 질문 → graph context + chunk evidence + prompt → 답변.
        </p>
      </div>

      <div className="card space-y-3 p-4">
        <div>
          <label className="label">질문</label>
          <textarea
            className="input h-24"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
        </div>
        <div className="flex justify-end">
          <button
            className="btn-primary"
            disabled={!question || run.isPending}
            onClick={() => {
              setError(null);
              run.mutate();
            }}
          >
            {run.isPending ? "질의 중…" : "질의 실행"}
          </button>
        </div>
      </div>

      {error ? (
        <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {error}
        </div>
      ) : null}

      {resp || detail.data ? (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_360px]">
          <div className="space-y-3">
            <div className="card p-4">
              <h3 className="text-sm font-semibold">Answer</h3>
              <div className="mt-2 whitespace-pre-wrap text-sm leading-7 text-slate-800">
                {detail.data?.answer ?? resp?.answer ?? "(no answer)"}
              </div>
            </div>

            {resp ? (
              <div className="grid grid-cols-2 gap-3">
                <div className="card p-3">
                  <div className="text-xs uppercase text-slate-500">graph context</div>
                  <div className="mt-1 text-sm">
                    seeds: <b>{resp.graph_context.seed_entities.length}</b>
                  </div>
                  <div className="text-sm">
                    triples: <b>{resp.graph_context.triple_count}</b>
                  </div>
                </div>
                <div className="card p-3">
                  <div className="text-xs uppercase text-slate-500">document evidence</div>
                  <div className="mt-1 text-sm">
                    chunks: <b>{resp.document_evidence.chunk_count}</b>
                  </div>
                </div>
              </div>
            ) : null}

            {detail.data?.graph_context_json ? (
              <Collapsible title="Graph Context (JSON)">
                <JsonViewer data={detail.data.graph_context_json} />
              </Collapsible>
            ) : null}
            {detail.data?.retrieved_chunks_json ? (
              <Collapsible title="Document Evidence (JSON)">
                <JsonViewer data={detail.data.retrieved_chunks_json} />
              </Collapsible>
            ) : null}
            {detail.data?.final_prompt ? (
              <Collapsible title="Rendered Prompt">
                <pre className="overflow-auto rounded-md border border-slate-200 bg-slate-50 p-3 font-mono text-xs leading-relaxed text-slate-800">
                  {detail.data.final_prompt}
                </pre>
              </Collapsible>
            ) : null}
            {detail.data ? (
              <div className="card flex flex-wrap gap-4 p-3 text-xs text-slate-600">
                <div>provider: <b>{detail.data.model_provider ?? "-"}</b></div>
                <div>model: <b>{detail.data.model_name ?? "-"}</b></div>
                <div>tokens: <b>{detail.data.token_estimate ?? "-"}</b></div>
                <div>latency: <b>{detail.data.latency_ms ?? "-"} ms</b></div>
                {detail.data.error_message ? (
                  <div className="text-red-600">err: {detail.data.error_message}</div>
                ) : null}
              </div>
            ) : null}
          </div>

          <div className="card p-3">
            <h3 className="text-sm font-semibold">최근 질의 로그</h3>
            <div className="mt-2 space-y-1">
              {(logs.data ?? []).map((l) => (
                <button
                  key={l.id}
                  onClick={() => setSelectedLog(l.id)}
                  className={
                    "w-full rounded border px-2 py-1.5 text-left text-xs " +
                    (selectedLog === l.id
                      ? "border-brand-400 bg-brand-50"
                      : "border-slate-200 hover:bg-slate-50")
                  }
                >
                  <div className="line-clamp-1 font-medium text-slate-800">{l.question}</div>
                  <div className="text-[10px] text-slate-500">
                    {formatDate(l.created_at)} · {shortId(l.id)}
                  </div>
                </button>
              ))}
              {!logs.data?.length ? (
                <div className="py-4 text-center text-xs text-slate-400">로그 없음</div>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Collapsible({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="card overflow-hidden">
      <button
        className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-slate-50"
        onClick={() => setOpen(!open)}
      >
        <span className="font-semibold">{title}</span>
        <span className="text-slate-400">{open ? "▾" : "▸"}</span>
      </button>
      {open ? <div className="border-t border-slate-100 p-3">{children}</div> : null}
    </div>
  );
}
