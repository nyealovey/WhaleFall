# WhaleFall UI image generation

This folder contains the page-level image generation batch for a compact modern redesign of the WhaleFall web UI.

## Status

Live image generation is not complete in this environment because:

- `OPENAI_API_KEY` is not set.
- The active `python3` environment does not have the `openai` package.

## Generate

Run from the repository root after setting `OPENAI_API_KEY`:

```bash
uv run --with openai --with pillow python3 /Users/apple/.codex/skills/imagegen/scripts/image_gen.py generate-batch \
  --input design/whalefall-ui-imagegen.jsonl \
  --out-dir design \
  --concurrency 3 \
  --force
```

Dry-run validation:

```bash
python3 /Users/apple/.codex/skills/imagegen/scripts/image_gen.py generate-batch \
  --input design/whalefall-ui-imagegen.jsonl \
  --out-dir design \
  --dry-run
```

## Design Direction

- Compact modern DBA operations console.
- Dense but readable tables, filters, status chips, charts, and task panels.
- Light industrial control-console style using WhaleFall's current orange/cyan/green/red signal palette.
- Consistent top navigation, compact page headers, 8px card radius, restrained shadows.
- Output is one desktop mockup image per page.
