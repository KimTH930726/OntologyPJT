import axios, { AxiosError } from "axios";

const baseURL = import.meta.env.VITE_API_BASE ?? "";

export const api = axios.create({
  baseURL,
  headers: { "Content-Type": "application/json" },
});

export type ApiErrorPayload = {
  code?: string;
  message?: string;
  [k: string]: unknown;
};

export function apiErrorMessage(err: unknown): string {
  if (err instanceof AxiosError) {
    const detail = err.response?.data?.detail as ApiErrorPayload | string | undefined;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object") {
      return detail.message || detail.code || JSON.stringify(detail);
    }
    return err.message;
  }
  if (err instanceof Error) return err.message;
  return String(err);
}
