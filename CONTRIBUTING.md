# Contributing

Issues and pull requests are welcome. For a large change, open an issue first so we can agree on the approach.

## Setup

Follow the Quickstart in the [README](README.md). Run the tests before opening a pull request:

```bash
for t in test_store test_anonymize test_voice_anon test_interview test_agent test_markdown_strip test_session test_resume test_openai_audio test_silence test_monitoring; do
  uv run python -m tests.$t
done
cd client && npm run build
```

## Guidelines

- Keep pull requests small and focused on one change.
- Match the style of the code around your change.
- Schema changes: edit `server/store/models.py`, then `uv run alembic revision --autogenerate -m "..."` and review the
  generated file.
- New interview niche: add a pack file to `packs/` (see `packs/tech_behavioral.toml`). Packs are validated at startup.
- Never commit secrets or real CVs. Env files other than `*.example` are git-ignored.
