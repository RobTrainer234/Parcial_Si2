# AGENTS.md

## Project Overview
This repository contains two separate applications:

- `Backend/` → FastAPI backend
- `Frontend/` → Angular frontend

Treat them as separate apps with different responsibilities, commands, and dependencies.

---

## General Working Rules

- Make minimal, targeted changes.
- Do not refactor unrelated code.
- Do not rename, move, or delete files unless explicitly required.
- Do not introduce new dependencies unless clearly justified.
- If the task is ambiguous, prefer asking for the exact file or scope instead of guessing.
- Before editing multiple files, briefly state which files will be touched and why.
- Prefer deterministic, small edits over broad rewrites.

---

## Scope Boundaries

### Backend
Work inside `Backend/` only when the task is related to:
- API routes
- business logic
- database access
- schemas
- backend validation
- authentication
- backend configuration

### Frontend
Work inside `Frontend/` only when the task is related to:
- Angular components
- pages/views
- routing
- forms
- frontend services
- UI behavior
- HTTP/API consumption from the frontend

### Cross-cutting changes
If a task affects both apps, keep backend and frontend concerns clearly separated.

---

## Directories That Must Not Be Explored Or Modified Unless Explicitly Requested

Avoid reading, indexing, modifying, or reasoning over these directories unless absolutely necessary:

- `Backend/venv/`
- `Backend/__pycache__/`
- `Frontend/node_modules/`
- `Frontend/.angular/`
- `Frontend/dist/`
- `Frontend/build/`
- any cache, generated, compiled, or dependency folder

Do not waste time inspecting generated files.

---

## Backend Conventions

### Current Stack
- Framework: FastAPI
- Language: Python
- Expected environment: virtual environment inside `Backend/venv`

### Backend Structure Guidance
If backend structure needs improvement, prefer moving toward this layout:

```text
Backend/
├── app/
│   ├── main.py
│   ├── routers/
│   ├── services/
│   ├── schemas/
│   ├── models/
│   ├── db/
│   └── core/
├── venv/
├── requirements.txt
└── .env