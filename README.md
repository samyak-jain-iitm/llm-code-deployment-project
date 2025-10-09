# LLM Code Deployment - Student API (instructions)

## Setup (env)
Set environment variables:
- `STUDENT_SECRET` — the secret you provided in the Google Form (used to verify incoming requests).
- `GITHUB_TOKEN` — personal access token with `repo` scope (or Pages write permission) to create repositories and enable Pages. See GitHub docs for Pages API permission details. :contentReference[oaicite:3]{index=3}
- (optional) `GITHUB_OWNER` — organization name if you want to create repos in an organization; otherwise repo is created in the token owner account.

Example (Linux/macOS):
```bash
export STUDENT_SECRET="your-secret-from-form"
export GITHUB_TOKEN="ghp_xxx..."
export GITHUB_OWNER="my-org"   # optional
