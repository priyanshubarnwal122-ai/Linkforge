# LinkForge — Current State, Flaws, and AI Maintenance Plan

## 1. What has been built so far

LinkForge is a Python 3.12, FastAPI URL-shortening and link-analytics application. It currently includes:

- Short-link creation and public redirection through `/s/{short_code}`.
- User registration, password login, JWT access/refresh tokens, and optional Google OAuth login.
- PostgreSQL persistence through async SQLAlchemy and Alembic migrations.
- Redis support for caching and security/rate-limit related operations.
- Link controls including custom aliases, password protection, expiration, self-destruct links, and device-based routing.
- Click analytics including daily trends, hourly traffic, unique visitors, and referrer categories.
- QR-code generation for links.
- A browser dashboard served by the FastAPI application.
- Optional AI alias recommendations using Gemini, with optional Groq/OpenAI fallbacks and a deterministic fallback when no AI key is configured.
- Docker Compose for local PostgreSQL, Redis, API, and Adminer services.
- Render deployment configuration, health endpoints, migrations at startup, a pinned Python version, dependency lockfile, and offline unit tests.

The main manual configuration is kept in `.env`. Google OAuth uses `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and an exact callback URL. Gemini alias recommendations use the separate `GEMINI_API_KEY`. These credentials are optional for local URL-shortening, but production requires a strong `SECRET_KEY` and working database/Redis configuration.

## 2. Current flaws and risks

The project is functional, but it is not yet an autonomous API-maintenance system. The most important gaps are:

1. **AI scope is narrow.** The current AI integration only recommends aliases. It does not inspect application logs, trace failures, compare API contracts, diagnose regressions, create a repair plan, or verify a fix.
2. **No centralized error intelligence.** API errors are logged, but there is no structured incident record that groups repeated failures by endpoint, release, exception, or dependency.
3. **Limited automated API monitoring.** Health checks confirm that the process and dependencies are available, but they do not exercise important user flows such as login, link creation, redirect, QR generation, or analytics.
4. **No contract-regression gate.** OpenAPI routes exist, but there is no automated comparison against a versioned API contract to detect accidental changes to request fields, response fields, status codes, or authentication requirements.
5. **External integrations can fail silently from the user perspective.** Google OAuth and Gemini depend on external credentials, redirect configuration, quotas, model availability, and network access. The application has fallbacks in some paths, but operators do not receive a clear actionable diagnosis.
6. **Security and operations need continuous checks.** Secrets must remain outside Git, production keys must be rotated, rate limits and abuse controls should be tested, and dependency/container vulnerabilities should be scanned regularly.
7. **Recovery is mostly manual.** A developer must inspect logs, reproduce a failure, decide on a code change, run tests, deploy, and watch the result. There is no safe approval workflow for AI-generated changes.

## 3. Proposed active AI maintenance capability

The next product capability should be a controlled **LinkForge AI Reliability Agent**. It should not blindly edit production. Its job should be to observe, diagnose, propose, test, and request approval.

### Detection

- Collect structured request logs containing request ID, route, method, status code, latency, release version, and sanitized error information.
- Add an incident store for error fingerprints, first/last seen time, frequency, affected routes, and dependency context.
- Run scheduled synthetic checks for health, authentication, link creation, redirect, QR, analytics, Google OAuth configuration, and Gemini configuration.
- Compare the generated OpenAPI schema with the previous release and flag breaking changes.

### Diagnosis

- Group duplicate failures instead of creating one alert per request.
- Correlate failures with recent commits, deployments, migrations, environment changes, and dependency errors.
- Ask an LLM to produce a concise explanation with evidence, confidence, probable root cause, and affected users.
- Redact passwords, tokens, API keys, authorization headers, and personal data before any AI analysis.

### Safe resolution workflow

1. Create an incident summary and severity level.
2. Suggest the smallest fix or rollback, including the files and tests involved.
3. Reproduce the issue in an isolated environment.
4. Run `make test`, linting, API contract tests, security checks, and relevant synthetic checks.
5. Present the evidence and proposed patch for human approval.
6. Deploy only after approval, then monitor error rate and latency.
7. Automatically close the incident only after recovery criteria are met; otherwise roll back or escalate.

## 4. Recommended implementation order

1. Strengthen structured logging, request IDs, redaction, and incident persistence.
2. Add endpoint-level smoke tests and a versioned OpenAPI contract check.
3. Add deployment/error metrics and alert thresholds.
4. Build a read-only AI diagnosis service with evidence citations.
5. Add an approval-based patch/test workflow in a sandbox branch.
6. Add post-deployment verification, rollback rules, and an incident history dashboard.

The success criterion is not simply “an AI chatbot is connected.” The finished system should detect a real breakage, explain why it happened using application evidence, propose a bounded change, prove the change with repeatable tests, and leave a human-controlled audit trail.
