import { BrowserRouter, Route, Routes } from "react-router-dom";
import AppLayout from "../components/layout/AppLayout";
import CandidatePortalPage from "../pages/candidate/CandidatePortalPage";
import SubmissionSuccessPage from "../pages/candidate/SubmissionSuccessPage";
import RecruiterDashboardPage from "../pages/recruiter/RecruiterDashboardPage";
import HomePage from "../pages/shared/HomePage";
import NotFoundPage from "../pages/shared/NotFoundPage";
import PrivacyPolicyPage from "../pages/shared/PrivacyPolicyPage";
import TermsPage from "../pages/shared/TermsPage";

export default function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<HomePage />} />
          <Route path="candidate" element={<CandidatePortalPage />} />
          <Route path="candidate/success" element={<SubmissionSuccessPage />} />
          <Route path="recruiter" element={<RecruiterDashboardPage />} />
          <Route path="privacy" element={<PrivacyPolicyPage />} />
          <Route path="terms" element={<TermsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
