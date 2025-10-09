# LLM Code Deployment - Student API (instructions)

## Setup (env)
Set environment variables:
- `STUDENT_SECRET` — the secret provided by the student in the Google Form (used to verify incoming requests).
- `OPENAI_API_KEY` — The OPENAI API Key to interact with their LLM.
- `GITHUB_TOKEN` — personal access token with `repo` scope (or Pages write permission) to create repositories and enable Pages. See GitHub docs for Pages API permission details. :contentReference[oaicite:3]{index=3}
- `GITHUB_OWNER` — owner of the repo (github username).

Example (Linux/macOS):
```bash
export STUDENT_SECRET="your-secret-from-form"
export GITHUB_TOKEN="ghp_xxx..."
export GITHUB_OWNER="my-org"   # optional

