"""
Generates synthetic sample PDF resumes for testing the AI Resume Screener.
"""

import os
from pathlib import Path

SAMPLE_RESUMES = {
    "Alex_Rivera_Senior_AI_Engineer.pdf": [
        "Alex Rivera",
        "alex.rivera@email.com | (555) 019-2834 | github.com/alexrivera",
        "",
        "SUMMARY",
        "Senior Full-Stack AI Engineer with 5+ years of experience building scalable generative AI web applications.",
        "Proven expertise integrating Gemini API, FastAPI, Python, PostgreSQL, and Streamlit.",
        "",
        "SKILLS",
        "- Languages: Python, JavaScript, TypeScript, SQL",
        "- Frameworks & Tools: FastAPI, Streamlit, Docker, PostgreSQL, React, Pydantic",
        "- AI & Machine Learning: Google GenAI SDK (Gemini), Prompt Engineering, Structured Outputs, LangChain",
        "- Cloud & DevOps: GCP, Cloud Run, Docker, Git CI/CD",
        "",
        "EXPERIENCE",
        "Lead AI Engineer | Apex Cloud Solutions (2022 - Present)",
        "- Architected end-to-end document processing pipelines using Gemini API and Pydantic structured schemas.",
        "- Built high-throughput microservices using FastAPI and PostgreSQL handling 2M+ daily requests.",
        "- Developed internal recruiter screening tools using Streamlit and Docker on Google Cloud Platform.",
        "",
        "Full-Stack Developer | InnovateTech Labs (2019 - 2022)",
        "- Developed responsive web frontends with React and robust RESTful APIs in Python.",
        "- Implemented automated CI/CD pipelines reducing deployment friction by 40%.",
        "",
        "EDUCATION",
        "B.S. in Computer Science | University of California, Berkeley",
    ],
    "Jordan_Lee_FullStack_Developer.pdf": [
        "Jordan Lee",
        "jordan.lee@email.com | (555) 482-1920",
        "",
        "PROFESSIONAL SUMMARY",
        "Full-Stack Web Developer with 3 years of experience specializing in React, Node.js, and Python backend services.",
        "Experienced in building RESTful APIs, database design, and cloud containerization.",
        "",
        "TECHNICAL SKILLS",
        "- Core: Python, JavaScript, Node.js, Express, React, HTML5, CSS3",
        "- Databases: PostgreSQL, MongoDB, Redis",
        "- DevOps: Docker, AWS ECS, Git, Linux",
        "- AI Exposure: Basic experimentation with OpenAI API endpoints",
        "",
        "PROFESSIONAL EXPERIENCE",
        "Full-Stack Developer | Nexus Interactive (2021 - Present)",
        "- Engineered client-facing web portals utilizing React, TypeScript, and Python REST APIs.",
        "- Integrated PostgreSQL databases with optimized query performance and indexing.",
        "- Containerized legacy backend services with Docker for scalable AWS deployments.",
        "",
        "Junior Web Developer | PixelCraft Studios (2020 - 2021)",
        "- Built modern responsive interfaces and integrated third-party RESTful APIs.",
        "",
        "EDUCATION",
        "B.S. in Software Engineering | State University",
    ],
    "Taylor_Smith_Junior_Analyst.pdf": [
        "Taylor Smith",
        "taylor.smith@email.com | (555) 773-9012",
        "",
        "OBJECTIVE",
        "Motivated Junior Data Analyst seeking to leverage foundational Python and data visualization skills.",
        "",
        "SKILLS",
        "- Python (Pandas, NumPy, Matplotlib)",
        "- SQL, Excel, Tableau, PowerBI",
        "- Statistical analysis and data cleaning",
        "",
        "WORK EXPERIENCE",
        "Junior Data Analyst | MetricFlow Analytics (2023 - Present)",
        "- Cleaned and aggregated weekly sales datasets using Python Pandas and SQL.",
        "- Built executive dashboards in Tableau to track revenue KPIs.",
        "- Automated repetitive reporting workflows with Python scripts.",
        "",
        "EDUCATION",
        "B.A. in Economics & Statistics (2023)",
    ],
}


def build_minimal_pdf(lines: list[str]) -> bytes:
    """Builds a valid text-selectable single-page PDF with Helvetica font."""
    # Generate content stream with text commands
    stream_lines = ["BT", "/F1 10 Tf", "50 750 Td", "14 TL"]
    for line in lines:
        sanitized_line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if sanitized_line.startswith("SUMMARY") or sanitized_line.startswith("SKILLS") or sanitized_line.startswith("EXPERIENCE") or sanitized_line.startswith("EDUCATION") or sanitized_line.startswith("OBJECTIVE") or sanitized_line.startswith("PROFESSIONAL"):
            stream_lines.append(f"T* ({sanitized_line}) Tj")
        elif not sanitized_line:
            stream_lines.append("T* () Tj")
        else:
            stream_lines.append(f"({sanitized_line}) Tj T*")
    stream_lines.append("ET")
    content_stream = "\n".join(stream_lines).encode("latin1", errors="replace")

    # Assemble PDF objects
    obj1 = b"1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n"
    obj2 = b"2 0 obj\n<</Type/Pages/Count 1/Kids[3 0 R]>>\nendobj\n"
    obj3 = (
        b"3 0 obj\n<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R"
        b"/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>\nendobj\n"
    )
    obj4 = b"4 0 obj\n<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>\nendobj\n"
    obj5 = f"5 0 obj\n<</Length {len(content_stream)}>>\nstream\n".encode("ascii") + content_stream + b"\nendstream\nendobj\n"

    header = b"%PDF-1.4\n"
    offsets = [0]
    body = b""
    for obj in [obj1, obj2, obj3, obj4, obj5]:
        offsets.append(len(header) + len(body))
        body += obj

    xref_offset = len(header) + len(body)
    xref = f"xref\n0 6\n0000000000 65535 f \n".encode("ascii")
    for off in offsets[1:]:
        xref += f"{off:010d} 00000 n \n".encode("ascii")

    trailer = f"trailer\n<</Size 6/Root 1 0 R>>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    return header + body + xref + trailer


def main():
    out_dir = Path("sample_resumes")
    out_dir.mkdir(exist_ok=True)

    for filename, lines in SAMPLE_RESUMES.items():
        pdf_bytes = build_minimal_pdf(lines)
        file_path = out_dir / filename
        file_path.write_bytes(pdf_bytes)
        print(f"Generated sample PDF: {file_path} ({len(pdf_bytes)} bytes)")


if __name__ == "__main__":
    main()
