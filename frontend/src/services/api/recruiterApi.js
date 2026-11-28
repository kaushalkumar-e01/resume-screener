import { apiRequest } from "./client";

export const recruiterApi = {
  login: (user_id, password) =>
    apiRequest("/recruiter/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id, password }),
    }),
  logout: (token) =>
    apiRequest("/recruiter/logout", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    }),
  checkSession: (token) =>
    apiRequest("/recruiter/session", {
      headers: { Authorization: `Bearer ${token}` },
    }),
  getDashboard: (token) =>
    apiRequest("/recruiter/dashboard", {
      headers: { Authorization: `Bearer ${token}` },
    }),
  uploadResumes: (token, files) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    return apiRequest("/recruiter/upload", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: fd,
    });
  },
  deleteCandidate: (token, id) =>
    apiRequest(`/recruiter/candidates/${encodeURIComponent(id)}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    }),
  deleteAllCandidates: (token) =>
    apiRequest("/recruiter/candidates", {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    }),
  runScreening: (token, job_description) =>
    apiRequest("/recruiter/screen", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ job_description }),
      timeoutMs: 180_000,
    }),
};

