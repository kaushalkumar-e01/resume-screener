import { candidateApi } from "./candidateApi";
import { recruiterApi } from "./recruiterApi";

const TOKEN_KEY = "ai_screener_recruiter_token";
const CACHE_TTL_MS = 30_000;

const cache = new Map();
const inFlight = new Map();

function getCached(key) {
  const entry = cache.get(key);
  if (!entry) return null;
  if (Date.now() > entry.expiresAt) {
    cache.delete(key);
    return null;
  }
  return entry.data;
}

function setCached(key, data, ttlMs = CACHE_TTL_MS) {
  cache.set(key, { data, expiresAt: Date.now() + ttlMs });
}

export function invalidatePrefetch(key) {
  if (key) {
    cache.delete(key);
  } else {
    cache.clear();
  }
}

export async function getCandidateConfigCached() {
  const key = "candidate_config";
  const cached = getCached(key);
  if (cached) return cached;

  if (inFlight.has(key)) return inFlight.get(key);

  const promise = candidateApi
    .getConfig()
    .then((data) => {
      setCached(key, data, 5 * 60_000);
      return data;
    })
    .finally(() => inFlight.delete(key));

  inFlight.set(key, promise);
  return promise;
}

export function prefetchCandidateConfig() {
  getCandidateConfigCached().catch(() => {});
}

export async function getRecruiterDashboardCached(token) {
  if (!token) return null;
  const key = `recruiter_dashboard:${token.slice(0, 12)}`;
  const cached = getCached(key);
  if (cached) return cached;

  if (inFlight.has(key)) return inFlight.get(key);

  const promise = recruiterApi
    .getDashboard(token)
    .then((data) => {
      setCached(key, data, 15_000);
      return data;
    })
    .finally(() => inFlight.delete(key));

  inFlight.set(key, promise);
  return promise;
}

export function prefetchRecruiterDashboardIfAuthorized() {
  const token = sessionStorage.getItem(TOKEN_KEY);
  if (!token) return;
  getRecruiterDashboardCached(token).catch(() => {});
}

