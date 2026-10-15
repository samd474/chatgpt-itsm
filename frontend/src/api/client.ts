import axios, { AxiosError } from "axios";

export const api = axios.create({
  baseURL: "/api",
  withCredentials: true,
  // Axios reads Django's (non-HttpOnly) CSRF cookie and echoes it in this header
  // on state-changing requests. The session cookie itself stays HttpOnly.
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
  headers: {
    Accept: "application/json",
  },
});

export function apiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: string; [key: string]: unknown }>;
    const data = axiosError.response?.data;
    if (data && typeof data.detail === "string") return data.detail;
    if (data && typeof data === "object") {
      const first = Object.values(data)[0];
      if (Array.isArray(first) && typeof first[0] === "string") return first[0];
      if (typeof first === "string") return first;
      if (first && typeof first === "object") {
        const nested = Object.entries(first as Record<string, unknown>)[0];
        if (nested) return `${nested[0]}: ${String(nested[1])}`;
      }
    }
    if (axiosError.response?.status === 403) {
      return "The server rejected this request. Check CSRF configuration and your permissions.";
    }
    if (axiosError.response?.status === 401) return "Your session is not authenticated.";
    if (axiosError.message) return axiosError.message;
  }
  return "An unexpected error occurred.";
}
