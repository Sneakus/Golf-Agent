# No live generation

These rules mirror `.cursor/rules/no-live-generation.mdc`. Keep both files in step.

- Never set `GOLF_LIVE`.
- Never run a live generation eval.
- Never make Anthropic API calls.
- Never run `generate.py`, `telegram_bot.py` or `eval_service.py` in a way that could call the Anthropic API.

Allowed:

- Offline work: reading, editing and testing code without network calls to Anthropic.
- Generation in replay mode.
- Retrieval scripts and `evaluate.py`, which use OpenAI embeddings only.
