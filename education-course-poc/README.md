# The First Leash Docusaurus POC

This is an isolated proof of concept for a public The First Leash guide shell.

Scope:
- no production route integration
- no auth
- no saved progress
- no checkout
- no magic link
- no backend dependency at runtime

The docs content is generated from the current repo curriculum source in `backend/services/education_catalog.py`.

## Run locally

```bash
npm install
npm start
```

## Build

```bash
npm run build
```

## Regenerate content

From the repo root:

```bash
python3 scripts/export_education_course_content.py
```
