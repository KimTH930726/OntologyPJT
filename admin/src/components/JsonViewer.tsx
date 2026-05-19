export default function JsonViewer({ data }: { data: unknown }) {
  return (
    <pre className="overflow-auto rounded-md border border-slate-200 bg-slate-50 p-3 text-xs leading-relaxed text-slate-800">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}
