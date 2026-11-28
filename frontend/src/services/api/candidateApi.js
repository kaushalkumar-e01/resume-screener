import { apiRequest } from "./client";

export const candidateApi = {
  health: () => apiRequest("/health", { timeoutMs: 8000 }),
  getConfig: () => apiRequest("/candidate/config"),
  syncEmail: (session_id, email) =>
    apiRequest("/candidate/sync-email", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id, email }),
    }),
  sendOtp: (session_id, email) =>
    apiRequest("/candidate/send-otp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id, email }),
    }),
  verifyOtp: (session_id, email, otp) =>
    apiRequest("/candidate/verify-otp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id, email, otp }),
    }),
  submitApplication: (formData) =>
    apiRequest("/candidate/submit", {
      method: "POST",
      body: formData,
    }),
};

