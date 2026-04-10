# Phase 1.5A — Subdomain Routing Design

**Date:** 2026-04-10

## Goal

Make `aditya.tapshalkar.com` the canonical URL for the portfolio. Redirect `tapshalkar.com` and `www.tapshalkar.com` to it. Fix the knowledge graph not loading on the subdomain (CORS mismatch).

## Architecture

All changes are in Terraform (`infra/`) and the FastAPI backend config. No frontend changes. The GCP load balancer URL map gains a host-based redirect rule for the apex and www hosts. The managed SSL cert is updated to cover the new subdomain. CORS is widened to `*.tapshalkar.com` to cover all current and future subdomains.

## Changes

### DNS (manual, Route53)
- Add A record: `aditya.tapshalkar.com` → `34.149.115.30`
- Existing records for `tapshalkar.com` and `www.tapshalkar.com` stay (they still need to resolve to the LB for the redirect to work)

### Terraform — `infra/variables.tf`
- Add `subdomain` variable (default `"aditya"`)

### Terraform — `infra/cdn.tf`
- Update `google_compute_managed_ssl_certificate` domains to include `aditya.tapshalkar.com`
- Update CDN URL map:
  - Add host rule for `aditya.tapshalkar.com` → `main` path matcher (serves content)
  - Change host rules for `tapshalkar.com` + `www.tapshalkar.com` → redirect to `https://aditya.tapshalkar.com` using `url_redirect` with `host_redirect` and `https_redirect = true`

### Backend — `backend/app/config.py`
- Change `allowed_origin: str` to `allowed_origin_pattern: str = "https://*.tapshalkar.com"`

### Backend — `backend/app/main.py`
- Pass `allow_origin_regex` to `CORSMiddleware` instead of `allow_origins`

### Backend — Cloud Run env var (Terraform `infra/cloud_run.tf`)
- Remove `ALLOWED_ORIGIN` env var (no longer needed as a single value)
- The pattern is hardcoded in config as a default; no secret required

## Contract

After this plan:
- `https://aditya.tapshalkar.com` → serves the site
- `https://tapshalkar.com` → 301 to `https://aditya.tapshalkar.com`
- `https://www.tapshalkar.com` → 301 to `https://aditya.tapshalkar.com`
- `GET /api/graph` responds with CORS headers for any `*.tapshalkar.com` origin
- SSL cert covers all three domains
