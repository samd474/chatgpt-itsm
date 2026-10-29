# chatgpt-itsm

Self-hostable IT service management platform: React + TypeScript (Vite), Django REST Framework,
PostgreSQL, Redis/Celery, Docker Compose and NGINX. Built following the *ITSM Project Build Guide*
(Phase 1), plus asset, contract, project and change management and an administrator console.

See [SECURITY.md](SECURITY.md) for the security review and controls.

## Quick start (development)

```bash
cp .env.example .env          # then set DJANGO_SECRET_KEY and POSTGRES_PASSWORD
docker compose up -d --build
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_roles     # Requester/Technician/Manager/Administrator/Auditor/CAB groups
docker compose exec backend python manage.py seed_slas      # business calendar + SLA policies
docker compose exec backend python manage.py seed_catalog   # three example catalog items
docker compose exec backend python manage.py createsuperuser
```

Open http://localhost:5173 and sign in. Superusers count as Administrators: use **Administration →
Users & roles** to create accounts, assign roles and support groups. Everything else an administrator
configures (support groups, categories, services, ticket templates, queues, custom fields, catalog items,
SLA policies, business hours, email templates, asset types, locations) lives under **Administration**.
Django admin (`/admin/`) remains available for advanced edits.

Malware scanning is optional in development (`docker compose --profile scan up -d clamav`, then set
`CLAMAV_HOST=clamav` in `.env`); it is always on, and fails closed, in production.

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
| `audit` + reports | `reports` | Append-only `AuditEvent`, service desk report, CSV exports (background for large ones), staged CSV import |
| — | `core` | Shared permissions, audited CRUD viewsets, custom field definitions, ClamAV scanner, auth backend |
| — | `assets` | Asset types, locations, assets, relationships, ticket links, history |
| — | `contracts` | Vendors, contracts, renewal reminders (financial fields hidden from technicians) |
| — | `projects` | Projects, members, milestones, tasks with dependencies |
| — | `changes` | Change requests, CAB approvals, scheduling, conflict detection, calendar |
| — | `solutions` | Knowledge base: articles (draft → published → retired, public or staff-only), search, links to tickets |

`rules` is an empty placeholder for a later phase.

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
| `GET/POST /api/help-requests/{id}/tasks/`, `PATCH /api/tasks/{id}/` | Fulfilment tasks |
| `GET /api/queues/`, `GET /api/queues/{id}/tickets/` | Admin-defined queues |
| `GET /api/ticket-templates/`, `GET /api/custom-fields/?entity=` | Templates and custom field definitions |
| `/api/assets/items/`, `/api/assets/types/`, `/api/assets/locations/` | Asset management |
| `/api/contracts/items/`, `/api/contracts/vendors/` | Contract management |
| `/api/projects/items/`, `/api/projects/tasks/`, `/api/projects/milestones/` | Project management |
| `/api/changes/items/` (+ `transition/`, `conflicts/`, `calendar/`), `/api/changes/approvals/` | Change management |
| `/api/admin/users/`, `/api/admin/roles/`, `/api/admin/catalog-items/`, `/api/admin/sla-policies/`, `/api/admin/business-calendars/`, `/api/admin/notification-templates/` | Administrator console |
| `GET /api/exports/`, `GET /api/exports/{id}/download/` | Background export files (owner only) |
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

Frontend smoke tests open every screen of the production build in Chromium with the API mocked in the
browser, so they need no backend. From `frontend/`:

```bash
npx playwright install chromium   # once
npm run build && npm run test:e2e
```

For editor tooling outside Docker: `python -m venv .venv && .venv/bin/pip install -r backend/requirements-dev.txt`.
Type-check the backend with `.venv/bin/basedpyright` from the repository root.

### Backend dependencies

Each `.in` file lists direct dependencies and compiles to a fully pinned `.txt` lock:

- `backend/requirements.in` → `requirements.txt`: what the app needs to run. The production image installs
  only this.
- `backend/requirements-dev.in` → `requirements-dev.txt`: the above plus test and type-check tools, at the
  same versions. The development image, CI and local tooling install this.

After editing a `.in` file, or to pick up newer versions, regenerate both locks with pip-tools from
`backend/`, production first since the dev lock is constrained by it:

```bash
pip install pip-tools==7.6.2
pip-compile --strip-extras --no-emit-index-url --output-file requirements.txt requirements.in
pip-compile --strip-extras --no-emit-index-url --output-file requirements-dev.txt requirements-dev.in
# To upgrade, add --upgrade to both commands.
```

CI fails if either lock is out of date with its `.in` file.

## Production

- `compose.prod.yml` builds `backend/Dockerfile.prod` (Gunicorn, non-root user, collected static files).
- `infra/nginx/itsm.conf` terminates TLS, serves `frontend/dist`, proxies `/api` and `/admin`, and never
  serves `/media` directly.
- Set `DJANGO_DEBUG=0`, real `DJANGO_ALLOWED_HOSTS` / `DJANGO_CSRF_TRUSTED_ORIGINS`, SMTP settings, and
  raise `DJANGO_HSTS_SECONDS` only once HTTPS works.
- Backups: `scripts/backup.sh` (pg_dump custom format) and `scripts/restore-test.sh` to prove a restore.
  Back up the `media_data` volume separately.

## Known gaps

- Catalog fulfilment tasks are created from templates but have no SLA of their own yet.
- Asset discovery/import from external inventory tools isn't built; use the API or Django admin.
- Change approvals use the CAB role; per-service approver groups would be a natural next step.
