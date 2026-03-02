---
name: zentable
description: "Documentation/adapter bundle for ZenTable workflows. Runtime code is provided via pinned GitHub release."
homepage: https://github.com/con2000us/zenTable
metadata:
  openclaw:
    emoji: "📊"
    requires:
      bins: ["python3", "google-chrome"]
allowed-tools: ["exec", "read", "write"]
---

# ZenTable Skill (ClawHub text-only package)

## Package type

This package is intentionally **text-only** for current ClawHub validator compatibility.
It provides workflow instructions and policy, while runnable source code is distributed via a pinned GitHub release.

## TL;DR

ZenTable helps agents convert messy table-like content into clean, decision-ready table outputs (mobile/desktop friendly).

Accepted input classes:
- text-based content (raw text tables, long responses)
- structured JSON
- screenshots / real-world photos (via OCR-assisted workflow)

Core output capabilities:
- CSS + PIL rendering
- sorting / filtering / pagination
- optional highlighting and PNG/TXT side output

## Runtime & security note

- Runtime code is **not bundled in this text-only package**.
- Use only the pinned release in `INSTALL.md`.
- Review code/dependencies before first execution.
- For first-time setup/execution, require explicit user confirmation.

## Known limitations

- ASCII output is beta/experimental and can vary across platforms.
- Current validation focus is Discord-first; other channels may need formatting adaptation.

## Contact

- GitHub Issues: https://github.com/con2000us/zenTable/issues
- Maintainer: @con2000us (Discord)
