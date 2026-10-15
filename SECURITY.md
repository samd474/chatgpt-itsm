# Security review

Review of the ITSM platform (Django REST API, React SPA, Celery, PostgreSQL, Redis) against the
OWASP Top 10 / API Security Top 10. Each finding lists what was found and how it is handled.
Regression tests for these cases live in `backend/*/tests.py` (search for the scenario names below).

## Summary of findings fixed in this review

| # | Severity | Finding | Fix |
|---|----------|---------|-----|
| 1 | High | **Privilege escalation via Django admin.** Stock `UserAdmin` lets any staff user with `change_user` set `is_superuser`, `user_permissions` or groups on any account, including their own. | `ITSMUserAdmin` makes privileged fields read-only and hides superusers for non-superusers. Role changes go through the audited admin API. (`test_django_admin_cannot_grant_superuser`) |
| 2 | High | **Disabled accounts kept working.** Setting `is_enabled=False` blocked new logins but existing sessions stayed valid. | `core.auth_backends.EnabledUserBackend` rejects disabled users in `user_can_authenticate`, which Django re-checks on every request, so sessions die immediately. (`test_disabled_user_session_stops_working`) |
| 3 | High | **Self-approval.** A requester who was also a Manager/approver could approve their own catalog request; change requesters could be CAB approvers of their own change. | Requesters are removed from approver lists and `decide_approval` refuses self-decisions. (`test_no_self_approval`, `test_requester_never_approves_own_change`) |
| 4 | High | **Login CSRF.** DRF only enforces CSRF for authenticated sessions, so `/api/auth/login/` accepted cross-site posts. | Login calls `SessionAuthentication().enforce_csrf()` explicitly. (`test_session_login_flow_with_csrf`) |
| 5 | Medium | **Malware.** Uploads were only extension/size checked. | ClamAV (`clamd` INSTREAM) scanning; fails closed when `DEBUG` is off; blocked files are audited (outside the rolled-back transaction). (`core/tests.py`) |
| 6 | Medium | **Stored content-type trusted on download.** | Downloads are always `application/octet-stream` + `Content-Disposition: attachment` + `nosniff`, so uploaded HTML/SVG can't execute. |
| 7 | Medium | **Format-string injection in admin-editable email templates.** `str.format` allows `{x.__class__.__mro__}` attribute traversal. | Templates are parsed with `string.Formatter`; only whitelisted bare placeholders are accepted. (`test_notification_templates_reject_attribute_access`) |
| 8 | Medium | **Queue filters as an injection vector.** Admin-defined queues could have been stored as raw ORM lookups. | Queue filters are a fixed vocabulary validated server-side and translated to explicit lookups; queues only ever *narrow* the viewer's existing scope. (`test_queue_filters_validated`, `test_queue_never_widens_visibility`) |
| 9 | Medium | **Requester-controlled routing.** Ticket templates with an assignment group would have required trusting the client. | `template` is sent by id; the server applies the template's routing and refuses staff-only templates. |
| 10 | Medium | **Stale authorization in background exports.** A queued export ran even if the user's export permission was revoked meanwhile. | `run_export` re-checks the permission and account state at run time; files are private, owner-only and expire. (`test_export_fails_if_permission_revoked`) |
| 11 | Medium | **Information disclosure.** Support-group member lists and user directories were readable by any user; Technicians saw contract values. | Member lists are admin-only, `/api/people/` and `/api/technicians/` are staff-only, contract financial fields are stripped for non-managers. |
| 12 | Medium | **Unbounded requests.** 10 MB JSON bodies, unlimited comment/description length, unbounded page sizes. | JSON bodies limited to 2 MB, text fields capped, `page_size` capped at 200, calendar ranges ≤ 120 days, search terms ≤ 200 chars. |
| 13 | Medium | **Rate limiting only on login.** | Global anon/user throttles plus scoped throttles for uploads and exports; NGINX `limit_req` on login endpoints. |
| 14 | Low | **Production misconfiguration.** Default Postgres password fallback, Redis without auth, no security headers on API responses. | Startup refuses `DEBUG=0` without a real secret key and DB password; prod Redis requires a password; CSP, Permissions-Policy, COOP, `Cache-Control: no-store` on API responses; `check --deploy` runs in CI. |
| 15 | Low | **Supply chain.** No dependency vulnerability scanning. | CI runs `pip-audit` and `npm audit --audit-level=high`. |

## Controls verified (no change needed)

- **SQL injection:** all data access uses the Django ORM; the only raw SQL is the constant `SELECT 1` health check. Filters, search and ordering use fixed field allow-lists (`filterset_fields`, `search_fields`, `ordering_fields`).
- **XSS:** React escapes all output; no `dangerouslySetInnerHTML`; Django templates autoescape; CSV exports neutralise formula cells (`=`, `+`, `-`, `@`).
- **IDOR / BOLA:** every queryset starts from the user's scope (`visible_HelpRequests`, `visible_projects`, approver/owner filters). Linking tickets to assets or changes re-checks ticket visibility.
- **Mass assignment:** serializers declare explicit field lists; workflow fields (`status`, `requested_by`, `outcome`, actual times, `is_superuser`) are read-only and change only through service functions.
- **Audit integrity:** `AuditEvent` refuses update/delete in the model; the API and Django admin are read-only for it.
- **Sessions:** HttpOnly + SameSite=Lax cookies, `Secure` in production, 8-hour sliding expiry, rotation on login, invalidation on password change; admins can end a user's sessions.
- **Passwords:** Django validators (length, common, numeric, similarity) apply to admin-set passwords; passwords are never logged or audited.
- **Separation of duties:** auditors are read-only everywhere; administrators cannot change their own roles, disable themselves, edit superusers, or reset other administrators' passwords.

## Residual risks / recommendations

- Add MFA (e.g. via your SSO provider) before exposing the service to the internet.
- Run ClamAV with signature updates (`freshclam`) and monitor the scanner's health.
- Consider `django-axes`-style per-account lockout in addition to rate limiting.
- Put the database and Redis on a private network and back up `media_data` with encryption.
- Review audit logs for `attachment.malware_blocked`, `auth.login_failed` spikes and `admin.user.*` events.

## Reporting

Report suspected vulnerabilities privately to the service desk security contact rather than in a public issue.
