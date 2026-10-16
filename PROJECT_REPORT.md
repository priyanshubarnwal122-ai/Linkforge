# LinkforgeAI — Product and Capability Report

## 1. Executive summary

LinkforgeAI is a production-oriented URL shortening and link-management platform built around the original Linkforge URL shortener.

Its primary product is still URL shortening:

1. A user creates a short link from a destination URL.
2. Linkforge stores the link and its ownership information.
3. Visitors open the short link.
4. Linkforge validates the link state and redirects the visitor to the destination.
5. Redirect activity is recorded for analytics and reliability monitoring.

The AI and operational features are intentionally built around that core. Normal link creation and redirection do not depend on an AI provider being configured. If an optional AI integration is unavailable, the URL-shortening product remains useful.

## 2. What the product can do

### URL shortening and management

- Create short URLs from HTTP and HTTPS destinations.
- Generate unique short codes.
- Create custom aliases such as `/my-resume`.
- List links owned by the authenticated user.
- Retrieve individual links.
- Enable or disable links.
- Soft-delete links.
- Redirect visitors through `/s/{short_code}` or an alias route.
- Support link expiration dates.
- Support maximum-click limits.
- Support password-protected links.
- Support one-time, self-destructing links.
- Support separate iOS and Android destinations.
- Generate QR codes that point to the short link rather than directly to the destination.
- Fetch page titles in a best-effort background task.

### Security controls for destinations

LinkforgeAI validates destination URLs before storing them.

It accepts only:

- `http://`
- `https://`

It rejects:

- Unsupported schemes such as `javascript:`.
- URLs with embedded usernames or passwords.
- `localhost` destinations.
- Loopback addresses.
- Private-network addresses.
- Link-local addresses.
- Reserved IP addresses.

The background title-fetching feature applies the same destination validation so the service is not intended to act as an unrestricted server-side request proxy.

### Authentication and authorization

- User registration.
- Password-based login.
- JWT access tokens.
- Refresh-token rotation when Redis is available.
- Logout and refresh-token revocation when Redis is available.
- Bcrypt password hashing.
- Account ownership checks for link management.
- Ownership checks for analytics and QR-code endpoints.
- Optional Google OAuth configuration.
- Optional email-verification flow.
- Redis-backed failed-login lockout when Redis is available.
- Redis-backed link-creation rate limiting.

When Redis is unavailable, the application enters a degraded mode for optional Redis-backed protections rather than blocking the core URL-shortening path.

### Privacy-aware analytics

Redirect events can record:

- Click time.
- An anonymized IP-derived identifier.
- Browser category.
- Device category.
- Referrer category.
- UTC hour of the click.

The analytics API provides:

- Total clicks.
- Unique clicks.
- Today’s clicks.
- Last-seven-day activity.
- Top browsers.
- Top devices.
- Top referrers.
- Twenty-four-hour traffic heatmap.

The service does not require cookies or browser fingerprinting for these analytics.

### Reliability monitoring

The application records operational events asynchronously so telemetry does not intentionally block the normal redirect response.

Events can include:

- Redirect success.
- Redirect failures.
- Error status codes.
- Redirect latency measurements.
- Component names.
- Supporting evidence such as status code and latency.

Each HTTP response receives an `X-Request-ID` correlation identifier. A client can provide its own `X-Request-ID`, or the application generates one.

### Deterministic incident detection

LinkforgeAI includes a deterministic detector that examines recent persisted operational events.

The current rule detects elevated error activity by component over a recent time window and creates an incident with:

- Incident title.
- Severity.
- Status.
- Affected component.
- Start time.
- Summary.
- Supporting evidence.

Incident data is stored in PostgreSQL rather than kept only in memory.

### Evidence-backed investigation

The current baseline investigator works without an AI provider. It retrieves the operational events linked to an incident and returns:

- Observed facts.
- Event IDs.
- Event types.
- Timestamps.
- Measurements and stored evidence.
- A clearly labeled root-cause hypothesis.
- Confidence level.
- Unknowns and remaining uncertainty.
- A recommended next diagnostic step.

This is intentionally bounded. It does not claim that a hypothesis is a confirmed root cause when the stored evidence is insufficient.

### Approval-gated remediation

The current remediation policy has a small explicit allowlist:

- `acknowledge_incident`
- `resolve_incident`

Every remediation request records:

- The incident.
- The requested action.
- The requesting user.
- Request time.
- Approval status.
- Approving user.
- Approval time.
- Execution time.
- Execution result.

Execution is blocked until an authenticated, verified user approves the action. The system does not permit arbitrary shell commands or unrestricted production changes.

## 3. Dashboard capabilities

The existing vanilla HTML/CSS/JavaScript dashboard provides:

- Registration and login forms.
- URL shortening form.
- Custom alias input.
- Advanced link options.
- Link listing table.
- Copy-short-link action.
- QR-code access.
- Analytics modal with charts and breakdowns.
- Incident listing panel.
- Incident investigation action.
- Automatic stale-session recovery.

The dashboard uses backend data rather than fixed demonstration metrics.

If a browser stores an invalid or expired JWT, the frontend clears it, tells the user that the session expired, and reloads the login state.

## 4. Main API surface

### Health and documentation

```text
GET /api/v1/health/live
GET /api/v1/health/ready
GET /docs
```

### Authentication

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
GET  /api/v1/auth/me
GET  /api/v1/auth/verify-email
GET  /api/v1/auth/google/login
GET  /api/v1/auth/google/callback
```

### Links

```text
POST   /api/v1/links/
GET    /api/v1/links/
GET    /api/v1/links/{link_id}
PATCH  /api/v1/links/{link_id}/toggle
DELETE /api/v1/links/{link_id}
POST   /api/v1/links/recommend-alias
```

### Public redirection

```text
GET /s/{short_code}
GET /{short_code}
```

### Analytics and QR codes

```text
GET /api/v1/links/{link_id}/stats
GET /api/v1/links/{link_id}/qr
```

### Incidents

```text
GET  /api/v1/incidents/
POST /api/v1/incidents/detect
POST /api/v1/incidents/{incident_id}/investigate
```

### Remediation

```text
POST /api/v1/incidents/{incident_id}/actions
POST /api/v1/incidents/{incident_id}/actions/{action_id}/approve
POST /api/v1/incidents/{incident_id}/actions/{action_id}/execute
```

## 5. Data stored by the platform

PostgreSQL stores the following major tables:

| Table | Purpose |
|---|---|
| `users` | Accounts and authentication-related profile data |
| `links` | Destination URLs, aliases, ownership, expiry and link policies |
| `click_events` | Redirect analytics events |
| `operational_events` | Reliability and redirect monitoring events |
| `incidents` | Correlated reliability incidents and evidence |
| `incident_actions` | Approval and execution audit history |
| `alembic_version` | Database migration version |

## 6. Architecture

```text
Browser
  |
  v
FastAPI application
  |
  +--> Authentication and link APIs
  +--> Public redirect path
  +--> Analytics and QR endpoints
  +--> Incident and remediation APIs
  |
  +--> PostgreSQL
  |      +--> users
  |      +--> links
  |      +--> click_events
  |      +--> operational_events
  |      +--> incidents
  |      +--> incident_actions
  |
  +--> Redis (optional operational acceleration)
         +--> rate limiting
         +--> failed-login lockout
         +--> refresh-token tracking
```

The system uses Alembic migrations. The container startup script waits for the database, applies migrations, and then starts Uvicorn.

## 7. Deployment capabilities

The repository includes:

- Python 3.12.8 runtime pin.
- Locked Python dependencies.
- Multi-stage Dockerfile.
- Non-root application container.
- Docker health check.
- Docker Compose configuration for API, PostgreSQL, Redis, and Adminer.
- Persistent Docker volumes for PostgreSQL and Redis.
- Alembic migration startup.
- Render Blueprint configuration.
- GitHub Actions CI configuration.
- `.env.example` without real credentials.
- README setup and troubleshooting instructions.

Local startup:

```bash
cp .env.example .env
docker compose up -d --build
```

Application URLs:

```text
Dashboard:  http://localhost:8000
API docs:   http://localhost:8000/docs
Adminer:    http://localhost:8080
```

On Windows, Docker Desktop must be running before Compose commands can work.

## 8. Verification currently included

The repository includes offline tests for:

- URL destination selection.
- URL validation and private-destination rejection.
- Incident detector metric calculation.
- Precision, recall, and F1 calculation.
- Remediation allowlist behavior.
- Rejection of unsafe remediation actions.

Useful commands:

```bash
python -m unittest discover -s tests -v
python -m compileall -q backend/app backend/alembic tests scripts
python -m ruff check backend/app --select E,F,W,I --ignore E501
docker compose config --quiet
```

The synthetic redirect evaluation reports metrics calculated from actual synthetic observations. Its results must not be interpreted as production traffic performance.

## 9. What is optional or limited today

The following capabilities are intentionally limited or optional:

- AI-provider investigations are not required for the baseline investigator to work.
- The current investigator is deterministic and evidence-based; it is not a full autonomous LLM operations agent.
- The remediation allowlist currently changes incident state only. It does not restart real infrastructure or alter database configuration.
- Redis-backed protections degrade safely when Redis is unavailable.
- Full production deployment still requires a hosting account, credentials, domain configuration, and operator approval.
- Production performance numbers have not been claimed from the synthetic test suite.
- Full browser end-to-end automation and large-scale load testing are not included in the offline test suite.
- The application currently uses polling/manual refresh for incident updates rather than WebSockets.

## 10. Recommended first demonstration

1. Start Docker Compose.
2. Open `http://localhost:8000`.
3. Register and log in.
4. Create a link to `https://example.com`.
5. Open the generated short URL.
6. Open the link’s **Stats** view.
7. Refresh the dashboard and inspect the incident panel.
8. Use Adminer only if you want to inspect the underlying records.

## 11. Product identity

LinkforgeAI is not primarily an AI chatbot or a decorative AI dashboard. It is a URL shortener with reliability engineering around it:

- The URL is the core product.
- Redirects remain the critical path.
- Monitoring is asynchronous where possible.
- Detection starts with deterministic rules.
- Investigation cites stored evidence.
- Remediation is approval-gated.
- Optional AI services are not required for basic link management.
