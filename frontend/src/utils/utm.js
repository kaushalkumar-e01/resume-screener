const UTM_STORAGE_KEY = "talentpulse_utm";

export function captureUtmParams(searchString) {
  if (!searchString) return null;
  const params = new URLSearchParams(searchString);
  const utm = {};
  for (const key of ["utm_source", "utm_medium", "utm_campaign"]) {
    const val = params.get(key);
    if (val && val.trim()) {
      utm[key] = val.trim().slice(0, 64);
    }
  }
  if (Object.keys(utm).length > 0) {
    sessionStorage.setItem(UTM_STORAGE_KEY, JSON.stringify(utm));
    return utm;
  }
  return null;
}

export function getStoredUtmParams() {
  try {
    const raw = sessionStorage.getItem(UTM_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

