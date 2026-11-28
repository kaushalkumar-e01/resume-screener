import { useEffect } from "react";

const DEFAULT_TITLE = "TalentPulse AI — Resume Screening System";
const DEFAULT_DESC =
  "AI-assisted resume screening platform with verified candidate intake and structured recruiter evaluation.";

export function useDocumentMeta({ title, description }) {
  useEffect(() => {
    document.title = title ? `${title} | TalentPulse AI` : DEFAULT_TITLE;
    const metaDesc = document.querySelector('meta[name="description"]');
    if (metaDesc) {
      metaDesc.setAttribute("content", description || DEFAULT_DESC);
    }
  }, [title, description]);
}

