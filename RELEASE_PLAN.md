# DataForge Studio — Release Assessment & Timeline

> Generated: 2026-03-15

---

## Overall Assessment

DataForge Studio is a **well-architected synthetic data generation platform** at approximately **80–85% production readiness**. The core value proposition (natural language → synthetic dataset/document) is implemented end-to-end. The infrastructure layer (AWS/EKS/Terraform/K8s) is production-grade. The main gaps are a handful of incomplete features, missing CI/CD automation, and lightweight auth.

### Scores

| Dimension | Score | Notes |
|---|---|---|
| Architecture | 9/10 | Clean agent/service/API separation; LangGraph multi-agent is solid |
| Backend code quality | 7/10 | Well-structured, good error handling, async throughout; SDV replication disabled |
| Frontend code quality | 7/10 | TypeScript + Zustand + SSE streaming; missing `package.json` is a blocker |
| Test coverage | 5/10 | 1,165 lines of tests across 6 files, but no coverage report; mostly unit/integration, no E2E |
| Documentation | 9/10 | Excellent README, quick-start, architecture docs, AWS guides |
| Infrastructure | 8/10 | Terraform + K8s fully written; no CI/CD pipeline yet |
| Security | 5/10 | API-key auth only; CORS wide open (`*`); no user management |

### Strengths

- **Zero-shot LLM schema inference** — natural language to relational schema with referential integrity, powered by Claude via AWS Bedrock
- **Real-time SSE streaming** — live job progress visible in UI
- **PII detection & replacement** — spacy NER with four replacement strategies (fake, hash, redact, tokenize)
- **Multi-format output** — structured data (CSV/JSON/Parquet) + documents (PDF, DOCX, JSON)
- **Production infra ready** — EKS autoscaling (3–20 replicas), ALB, S3 artifacts, Redis caching, Terraform-managed
- **TypeScript frontend** — type-safe API client, Zustand state, chat + schema + jobs + settings views
- **Good documentation** — docs for architecture, AWS setup, Bedrock quotas, K8s deployment, LangGraph config

### Critical Blockers (must fix before any deploy)

| # | Issue | Location | Impact |
|---|---|---|---|
| 1 | Missing `package.json` in `/frontend` | `/frontend/package.json` | Frontend cannot install or run |
| 2 | SDV replication raises `NotImplementedError` | `services/generation/sdv_wrapper.py`, `api/routes_replication.py` | Dataset replication feature broken |
| 3 | CORS set to `*` | `app/core/config.py` | Security risk in production |
| 4 | No CI/CD pipeline | `.github/` absent | No automated testing or deploy gate |

### Secondary Issues (fix before public launch)

- Hardcoded developer path in `QUICK_START.md` (`/Users/romainboluda/...`)
- `USE_S3=false` and `USE_REDIS=false` defaults are dev-only; production config not enforced
- API key auth is shared/static; no per-user credentials or rate limiting
- No database migrations system (Alembic or similar)
- Test coverage report not tracked; likely below 60%
- No E2E or smoke tests against a deployed environment
- OpenAPI docs (`/docs`) should be disabled in production

---

## Release Timeline

Today: **2026-03-15**. Assumes 1–2 developers working full-time.

### Phase 1 — Fix Blockers (Week 1, by 2026-03-22)

Goal: app runs end-to-end locally and in Docker.

| Task | Owner | Effort |
|---|---|---|
| Restore/generate `frontend/package.json` with correct Next.js 14 + dependencies | FE | 2h |
| Verify `npm install && npm run dev` works | FE | 1h |
| Re-implement or stub SDV replication with graceful error (not NotImplementedError) | BE | 4h |
| Lock CORS to explicit origins in `.env.example` and config | BE | 1h |
| Smoke-test full flow: prompt → schema inference → data generation → download | Both | 2h |
| Fix hardcoded paths in docs | Anyone | 30m |

**Exit criteria**: `docker-compose up` starts successfully; can generate a dataset via chat UI.

---

### Phase 2 — CI/CD & Test Coverage (Week 2, by 2026-03-29)

Goal: automated pipeline validates every PR; coverage above 70%.

| Task | Effort |
|---|---|
| GitHub Actions: `lint` (ruff/black) + `test` (pytest) on every PR | 3h |
| GitHub Actions: Docker build + push to ECR on merge to `main` | 3h |
| Add missing unit tests to reach ~70% backend coverage | 8h |
| Add frontend build check (`next build`) to CI | 1h |
| Enforce coverage threshold in CI (`--cov-fail-under=65`) | 1h |

**Exit criteria**: PR merges blocked if tests or lint fail; coverage report visible in CI output.

---

### Phase 3 — Hardening & Auth (Week 3, by 2026-04-05)

Goal: production-safe configuration; basic per-user auth.

| Task | Effort |
|---|---|
| Replace static API key with JWT-based auth (FastAPI Users or Auth0) | 1–2d |
| Add per-user rate limiting (slowapi or API gateway) | 4h |
| Production `.env` template with `USE_S3=true`, `USE_REDIS=true`, restricted CORS | 2h |
| Disable OpenAPI `/docs` in production (`ENVIRONMENT=production`) | 1h |
| Add structured health check that validates Redis + Bedrock connectivity | 2h |
| Secrets management via AWS Secrets Manager (replace env-file secrets) | 4h |

**Exit criteria**: Cannot access API without valid JWT; `/docs` returns 404 in prod mode.

---

### Phase 4 — Staging Deploy & QA (Week 4, by 2026-04-12)

Goal: running on AWS EKS staging environment; QA sign-off.

| Task | Effort |
|---|---|
| `terraform apply` for staging environment | 4h |
| Configure Route53 + ACM certificate for staging domain | 2h |
| Deploy via CI/CD to staging (Helm or kubectl apply) | 3h |
| Manual QA pass: all 4 UI views, all API endpoints, SSE streaming | 4h |
| Load test with k6 or locust (target: 50 concurrent users) | 4h |
| Fix issues found in QA | varies |

**Exit criteria**: QA sign-off on staging; no P0/P1 bugs outstanding.

---

### Phase 5 — Production Launch (Week 5, by 2026-04-19)

Goal: v1.0 live on production URL.

| Task | Effort |
|---|---|
| `terraform apply` for production environment | 2h |
| DNS cutover and TLS verification | 1h |
| Monitor logs and metrics for 24h post-launch | ongoing |
| Announce / update public docs with live URL | 2h |
| Tag `v1.0.0` release in GitHub | 30m |

**Target v1.0 launch date: 2026-04-19** (~5 weeks from today)

---

## Summary Roadmap

```
Week 1 (Mar 15–22)  ████████  Fix blockers — app runs end-to-end
Week 2 (Mar 22–29)  ████████  CI/CD + test coverage
Week 3 (Mar 29–Apr 5) ██████  Auth + production hardening
Week 4 (Apr 5–12)   ████████  Staging deploy + QA
Week 5 (Apr 12–19)  ████████  Production launch → v1.0
```

### What ships in v1.0

- Natural language → synthetic dataset generation (CSV, JSON, Parquet)
- Document generation (PDF, DOCX, JSON)
- PII detection and replacement
- Real-time job progress via SSE
- Chat UI + Schema editor + Job dashboard
- JWT authentication
- AWS EKS production deployment with autoscaling

### What is deferred to v1.1+

- Dataset replication via SDV statistical models
- Multi-user organization management
- Fine-grained RBAC
- Scheduled/recurring generation jobs
- Webhook notifications on job completion
- Usage analytics dashboard
