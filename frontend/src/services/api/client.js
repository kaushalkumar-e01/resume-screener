import { API_BASE_URL, REQUEST_TIMEOUT_MS } from "../../config/env";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function apiRequest(path, options = {}) {
  const controller = new AbortController();
  const timeoutMs = options.timeoutMs ?? REQUEST_TIMEOUT_MS;
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      signal: controller.signal,
    });

    let data = null;
    try {
      data = await res.json();
    } catch {
      data = null;
    }

    if (!res.ok) {
      const message =
        (data && (data.detail || data.message)) ||
        `Request failed with status ${res.status}`;
      throw new ApiError(message, res.status);
    }

    return data;
  } catch (err) {
    if (err.name === "AbortError") {
      throw new ApiError("Request timed out. Please try again.", 408);
    }
    if (err instanceof ApiError) throw err;
    throw new ApiError(err.message || "Network error contacting backend API.", 0);
  } finally {
    clearTimeout(timer);
  }
}

