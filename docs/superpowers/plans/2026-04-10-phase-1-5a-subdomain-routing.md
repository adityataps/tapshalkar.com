# Phase 1.5A — Subdomain Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `aditya.tapshalkar.com` the canonical URL. Redirect `tapshalkar.com` and `www.tapshalkar.com` to it. Fix knowledge graph CORS error on the subdomain.

**Architecture:** Pure Terraform + backend config changes. The GCP load balancer URL map gains host-based redirect rules for the apex and www hosts. The managed SSL cert is extended to cover `aditya.tapshalkar.com`. CORS is widened to `*.tapshalkar.com` via `allow_origin_regex` in FastAPI.

**Tech Stack:** Terraform, FastAPI CORSMiddleware, GCP URL Maps

**Prerequisites:** Phase 1 infra complete, LB IP is `34.149.115.30`, DNS A records for `tapshalkar.com` and `www.tapshalkar.com` already point to LB.

---

## File Map

```
infra/
├── variables.tf          # add subdomain variable
├── cdn.tf                # update cert domains, url map host rules
└── cloud_run.tf          # remove ALLOWED_ORIGIN env var

backend/
├── app/config.py         # replace allowed_origin with allowed_origin_pattern
└── app/main.py           # use allow_origin_regex in CORSMiddleware
```

---

## Task 1: DNS Record

- [ ] **Step 1: Add A record in Route53**

In AWS Route53, add:

| Type | Name | Value |
|------|------|-------|
| `A` | `aditya.tapshalkar.com` | `34.149.115.30` |

- [ ] **Step 2: Verify propagation**

```bash
dig +short aditya.tapshalkar.com
```

Expected: `34.149.115.30`

---

## Task 2: Terraform — Add Subdomain Variable

- [ ] **Step 1: Add `subdomain` variable to `infra/variables.tf`**

```hcl
variable "subdomain" {
  description = "Primary subdomain for the portfolio (e.g. aditya)"
  type        = string
  default     = "aditya"
}
```

- [ ] **Step 2: Add to `infra/terraform.tfvars`** (gitignored, edit locally)

```
subdomain = "aditya"
```

---

## Task 3: Terraform — Update SSL Cert and URL Map

- [ ] **Step 1: Read `infra/cdn.tf`** to understand current structure before editing.

- [ ] **Step 2: Update the managed SSL cert in `infra/cdn.tf`**

Replace:
```hcl
resource "google_compute_managed_ssl_certificate" "default" {
  name = "tapshalkar-cert"

  managed {
    domains = [var.domain, "www.${var.domain}"]
  }
}
```

With:
```hcl
resource "google_compute_managed_ssl_certificate" "default" {
  name = "tapshalkar-cert"

  managed {
    domains = [
      var.domain,
      "www.${var.domain}",
      "${var.subdomain}.${var.domain}",
    ]
  }
}
```

- [ ] **Step 3: Update the URL map in `infra/cdn.tf`**

Replace the existing `google_compute_url_map` `default` resource with:

```hcl
resource "google_compute_url_map" "default" {
  name            = "tapshalkar-url-map"
  default_service = google_compute_backend_bucket.static.id

  # Canonical subdomain — serves the site
  host_rule {
    hosts        = ["${var.subdomain}.${var.domain}"]
    path_matcher = "main"
  }

  # Apex and www — redirect to canonical subdomain
  host_rule {
    hosts        = [var.domain, "www.${var.domain}"]
    path_matcher = "redirect-to-subdomain"
  }

  path_matcher {
    name            = "main"
    default_service = google_compute_backend_bucket.static.id

    path_rule {
      paths   = ["/api/*"]
      service = google_compute_backend_service.backend.id
    }
  }

  path_matcher {
    name = "redirect-to-subdomain"

    default_url_redirect {
      host_redirect          = "${var.subdomain}.${var.domain}"
      https_redirect         = true
      redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
      strip_query            = false
    }
  }
}
```

- [ ] **Step 4: Commit Terraform changes**

```bash
git add infra/variables.tf infra/cdn.tf
git commit -m "feat(infra): add aditya subdomain, redirect apex/www to subdomain"
```

---

## Task 4: Terraform Apply

- [ ] **Step 1: Plan to verify changes**

```bash
cd infra
terraform plan
```

Expected: cert update (in-place), url_map update (in-place). No destroy/recreate.

- [ ] **Step 2: Apply**

```bash
terraform apply
```

Expected: `Apply complete!`

- [ ] **Step 3: Wait for cert to reprovision**

The cert now covers a third domain — GCP will re-verify `aditya.tapshalkar.com`:

```bash
watch -n 30 'gcloud compute ssl-certificates describe tapshalkar-cert --global --format="get(managed.status,managed.domainStatus)"'
```

Expected: all three domains show `ACTIVE`. Takes ~5–15 min after DNS propagates.

---

## Task 5: Fix CORS in Backend

- [ ] **Step 1: Read `backend/app/config.py`**

- [ ] **Step 2: Update `backend/app/config.py`**

Replace:
```python
class Settings(BaseSettings):
    gcs_bucket: str
    allowed_origin: str = "https://tapshalkar.com"
    resend_api_key: str = ""

    model_config = {"env_file": ".env"}
```

With:
```python
class Settings(BaseSettings):
    gcs_bucket: str
    allowed_origin_pattern: str = r"https://.*\.tapshalkar\.com"
    resend_api_key: str = ""

    model_config = {"env_file": ".env"}
```

- [ ] **Step 3: Read `backend/app/main.py`**

- [ ] **Step 4: Update `backend/app/main.py`**

Replace:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.allowed_origin, "http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
```

With:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=settings.allowed_origin_pattern,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
```

- [ ] **Step 5: Remove ALLOWED_ORIGIN from Cloud Run env vars in `infra/cloud_run.tf`**

Read `infra/cloud_run.tf`. Remove the `env` block for `ALLOWED_ORIGIN` if present (it was set to `https://tapshalkar.com` — no longer needed as an env var since the pattern is the default).

- [ ] **Step 6: Run backend tests**

```bash
cd backend
uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/config.py backend/app/main.py infra/cloud_run.tf
git commit -m "feat(backend): widen CORS to *.tapshalkar.com via allow_origin_regex"
```

---

## Task 6: Smoke Test

- [ ] **Step 1: Push and let CI/CD deploy backend**

```bash
git push
```

Watch GitHub Actions → Deploy Backend go green.

- [ ] **Step 2: Verify redirects**

```bash
# Apex should redirect to subdomain
curl -I https://tapshalkar.com/
# Expected: HTTP/2 301, location: https://aditya.tapshalkar.com/

# www should redirect
curl -I https://www.tapshalkar.com/
# Expected: HTTP/2 301, location: https://aditya.tapshalkar.com/

# Subdomain should serve the site
curl -I https://aditya.tapshalkar.com/
# Expected: HTTP/2 200
```

- [ ] **Step 3: Verify CORS from subdomain**

```bash
curl -I -H "Origin: https://aditya.tapshalkar.com" https://aditya.tapshalkar.com/api/graph
# Expected: access-control-allow-origin: https://aditya.tapshalkar.com
```

- [ ] **Step 4: Visit https://aditya.tapshalkar.com in browser**

Expected: site loads, knowledge graph renders without CORS errors in console.
