export const REVIEWER_STORAGE_KEY = "ontology-admin.reviewer";

export function getReviewer(): string {
  try {
    return localStorage.getItem(REVIEWER_STORAGE_KEY) || "admin";
  } catch {
    return "admin";
  }
}

export function setReviewer(name: string): void {
  try {
    localStorage.setItem(REVIEWER_STORAGE_KEY, name);
  } catch {
    // ignore
  }
}

export function formatDate(iso?: string | null): string {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

export function shortId(id?: string | null): string {
  if (!id) return "-";
  return id.slice(0, 8);
}

export function classNames(...xs: (string | false | null | undefined)[]): string {
  return xs.filter(Boolean).join(" ");
}

export function downloadJson(filename: string, data: unknown): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
