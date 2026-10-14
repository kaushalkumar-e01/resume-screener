# Secure Streamlit Deployment

## 1. Rotate the old Gemini key
The original development ZIP contained a `.env` file. Treat that Gemini API key as compromised and revoke it before deployment. Create a new key and store it only in Streamlit Secrets.

## 2. Recruiter credentials
The application supports a PBKDF2-SHA256 password hash. Generate one locally:

```bash
python -c "from utils import hash_password; print(hash_password('YOUR_NEW_PASSWORD'))"
```

Put the output into Streamlit Secrets:

```toml
GEMINI_API_KEY = "..."
RECRUITER_USER_ID = "..."
RECRUITER_PASSWORD_HASH = "salt_hex$pbkdf2_hash_hex"
```

A plaintext `RECRUITER_PASSWORD` is supported only as a local-development fallback. Do not use it for a public deployment.

## 3. GitHub contents
Commit source code, `requirements.txt`, `.streamlit/config.toml`, `.env.example`, and `.streamlit/secrets.toml.example`.

Do NOT commit:
- `.env`
- `.streamlit/secrets.toml`
- `venv/`
- `data/`
- `uploaded_resumes/`
- real candidate PDFs
- API keys or passwords

## 4. Important persistence limitation
SQLite and the uploaded-resume directory are persistent across Streamlit reruns and browser sessions while the same application filesystem remains available. Streamlit-hosted environments can replace/reset the application filesystem during some restarts, redeployments, or infrastructure changes. Therefore, this SQLite implementation is suitable for a controlled/demo deployment, but a production public service should move the database to a managed persistent database and uploaded resumes to durable object storage.

The application keeps the storage layer isolated in `database.py`, so this migration can be made later without rewriting the UI.
