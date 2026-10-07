# Baiita-n8n

Automation and content assets for the **Baiita** / **Sunnah Seed** children's media pipeline.

## Brand audio

- **[Sunnah Seed theme — “Morning Seeds”](assets/audio/sunnah-seed/README.md)**
  — the official 30-second seamless instrumental loop (`SS-THEME-001`).
  Warm wooden mallets at 90 BPM, one memorable motif, no vocals.
  Preview: `python tools/audio/sunnah_seed/preview_server.py 8080`

## Tooling

| Path | Purpose |
|---|---|
| `tools/audio/sunnah_seed/` | deterministic synthesis + mix + QC for the theme |
| `assets/audio/sunnah-seed/` | masters, stems, score, QC report, interactive player |
