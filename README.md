# chatgpt-itsm

Self-hostable IT service management platform: React + TypeScript (Vite), Django REST Framework,
PostgreSQL, Redis/Celery, Docker Compose and NGINX. Built following the *ITSM Project Build Guide*
(Phase 1).

## Quick start (development)

```bash
cp .env.example .env          # then set DJANGO_SECRET_KEY and POSTGRES_PASSWORD
docker compose up -d --build
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_roles     # Requester/Technician/Manager/Administrator/Auditor groups
docker compose exec backend python manage.py seed_slas      # business calendar + SLA policies
docker compose exec backend python manage.py seed_catalog   # three example catalog items
docker compose exec backend python manage.py createsuperuser
```

Open http://localhost:5173 and sign in. Add people to role groups and support groups in
Django admin (http://localhost:5173/admin/).

The browser only talks to the Vite origin; Vite proxies `/api` and `/admin` to Django, so the
session and CSRF cookies behave the same way they will behind NGINX in production.

## Where the guide's apps live

| Guide       | This repo      | Contents |
|-------------|----------------|----------|
| `accounts`  | `accounts`     | Custom `User`, login/logout/me/CSRF endpoints, `seed_roles` |
| `tickets`   | `helprequests` | `HelpRequests` (tickets), comments/private notes, attachments, approvals, support groups, categories, services |
| `catalog`   | `catalog`      | Catalog items, form-schema validation, request submission |
| `slas`      | `slas`         | Business calendars, SLA policies, due-date maths, pause/resume, Celery threshold check |
| `notifications` | `alerts`   | Notification events and per-recipient email deliveries |
| `audit` + reports | `reports` | Append-only `AuditEvent`, service desk report, CSV export helpers, staged CSV import |

`rules` and `solutions` are empty placeholders for later phases.

## API

| Endpoint | Purpose |
|----------|---------|
| `GET /api/auth/csrf/`, `POST /api/auth/login/`, `POST /api/auth/logout/`, `GET /api/auth/me/` | Session auth |
| `GET/POST /api/help-requests/`, `GET/PATCH /api/help-requests/{public_id}/` | Scoped tickets (no DELETE) |
| `POST /api/help-requests/{id}/transition/` | Lifecycle changes (timestamps, SLA, audit, notifications) |
| `GET/POST /api/help-requests/{id}/comments/` | Public replies and private notes |
| `GET/POST /api/help-requests/{id}/attachments/`, `GET .../attachments/{n}/download/` | Authorized uploads/downloads |
| `GET /api/help-requests/export/` | CSV export (needs `export_helprequests`) |
| `GET /api/catalog/items/`, `POST /api/catalog/items/{slug}/submit/` | Service catalog |
| `GET /api/approvals/`, `POST /api/approvals/{id}/decide/` | Approver queue |
| `GET /api/support-groups/`, `/api/categories/`, `/api/services/`, `/api/technicians/` | Lookups |
| `GET /api/reports/service-desk/` | Manager dashboard |
| `GET /api/audit/` | Audit search (Auditor/Administrator) |
| `POST /api/imports/`, `POST /api/imports/{id}/confirm/` | Staged CSV import (Administrator) |
| `GET /health/live`, `GET /health/ready` | Liveness / database + Redis readiness |

## Tests and checks

```bash
docker compose exec backend python -m pytest -q
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec frontend npm run lint
docker compose exec frontend npm run build
```

For editor tooling outside Docker: `python -m venv .venv && .venv/bin/pip install -r backend/requirements-dev.txt`.

## Production

- `compose.prod.yml` builds `backend/Dockerfile.prod` (Gunicorn, non-root user, collected static files).
- `infra/nginx/itsm.conf` terminates TLS, serves `frontend/dist`, proxies `/api` and `/admin`, and never
  serves `/media` directly.
- Set `DJANGO_DEBUG=0`, real `DJANGO_ALLOWED_HOSTS` / `DJANGO_CSRF_TRUSTED_ORIGINS`, SMTP settings, and
  raise `DJANGO_HSTS_SECONDS` only once HTTPS works.
- Backups: `scripts/backup.sh` (pg_dump custom format) and `scripts/restore-test.sh` to prove a restore.
  Back up the `media_data` volume separately.

## Known gaps

- `services.scan_file` is a placeholder malware-scan hook; wire in a real scanner before production.
- Large CSV exports run in the request; move them to a Celery task if they get slow.
- Catalog items have no fulfilment task templates yet; approved requests go straight to the assignment group.
