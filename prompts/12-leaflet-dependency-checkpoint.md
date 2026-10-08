# 12 — Leaflet dependency checkpoint

## Purpose

Apply CHECK → TAKE ACTION → VERIFY before introducing the only new map dependency.

## Selected instruction excerpt

> Determine whether Leaflet is already installed and declared directly. If it is missing, explain why it is required, its compatible version, the target frontend environment, the exact npm command, and the files that command will change. Ask for approval and stop.

After that read-only checkpoint, the user approved installing only Leaflet through the existing local npm environment. No plugin or global package was authorized.

## Outcome

- Leaflet `1.9.4` is a direct frontend dependency.
- `frontend/package.json` and `frontend/package-lock.json` are the only dependency declaration/lock files involved.
- The project-local import was verified before map implementation.
