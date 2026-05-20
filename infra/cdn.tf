# Static IP
resource "google_compute_global_address" "default" {
  name = "tapshalkar-lb-ip"
}

# GCS backend (for static files)
resource "google_compute_backend_bucket" "static" {
  name        = "tapshalkar-static-backend"
  bucket_name = google_storage_bucket.static_site.name
  enable_cdn  = true

  cdn_policy {
    cache_mode       = "CACHE_ALL_STATIC"
    default_ttl      = 3600
    max_ttl          = 86400
    negative_caching = true
  }
}

# Serverless NEG pointing to Cloud Run backend service
resource "google_compute_region_network_endpoint_group" "backend" {
  name                  = "backend-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region

  cloud_run {
    service = google_cloud_run_v2_service.backend.name
  }
}

# Backend service wrapping the NEG
resource "google_compute_backend_service" "backend" {
  name                  = "tapshalkar-backend-service"
  protocol              = "HTTPS"
  load_balancing_scheme = "EXTERNAL_MANAGED"

  backend {
    group = google_compute_region_network_endpoint_group.backend.id
  }

  security_policy = google_compute_security_policy.backend.id
}

# URL map: /api/* → Cloud Run, everything else → GCS
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

# TLS private key — stored in Terraform state (GCS bucket access-controlled)
resource "tls_private_key" "origin" {
  algorithm = "RSA"
  rsa_bits  = 2048
}

# CSR for Cloudflare to sign
resource "tls_cert_request" "origin" {
  private_key_pem = tls_private_key.origin.private_key_pem

  subject {
    common_name = var.domain
  }

  dns_names = [
    var.domain,
    "www.${var.domain}",
    "${var.subdomain}.${var.domain}",
  ]
}

# Cloudflare Origin CA certificate — trusted by Cloudflare's proxy, valid 15 years
resource "cloudflare_origin_ca_certificate" "default" {
  csr                = tls_cert_request.origin.cert_request_pem
  hostnames          = [var.domain, "www.${var.domain}", "${var.subdomain}.${var.domain}"]
  request_type       = "origin-rsa"
  requested_validity = 5475
}

# GCP self-managed cert using the Cloudflare-signed cert + key
resource "google_compute_ssl_certificate" "cloudflare_origin" {
  name        = "tapshalkar-cloudflare-origin-cert"
  private_key = tls_private_key.origin.private_key_pem
  certificate = cloudflare_origin_ca_certificate.default.certificate

  lifecycle {
    create_before_destroy = true
  }
}

# HTTPS proxy
resource "google_compute_target_https_proxy" "default" {
  name             = "tapshalkar-https-proxy"
  url_map          = google_compute_url_map.default.id
  ssl_certificates = [google_compute_ssl_certificate.cloudflare_origin.id]
}

# Forwarding rule (443)
resource "google_compute_global_forwarding_rule" "https" {
  name                  = "tapshalkar-https-rule"
  ip_address            = google_compute_global_address.default.address
  port_range            = "443"
  target                = google_compute_target_https_proxy.default.id
  load_balancing_scheme = "EXTERNAL_MANAGED"
}

# HTTP → HTTPS redirect
resource "google_compute_url_map" "redirect" {
  name = "tapshalkar-http-redirect"

  default_url_redirect {
    https_redirect         = true
    strip_query            = false
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
  }
}

resource "google_compute_target_http_proxy" "redirect" {
  name    = "tapshalkar-http-proxy"
  url_map = google_compute_url_map.redirect.id
}

resource "google_compute_global_forwarding_rule" "http" {
  name                  = "tapshalkar-http-rule"
  ip_address            = google_compute_global_address.default.address
  port_range            = "80"
  target                = google_compute_target_http_proxy.redirect.id
  load_balancing_scheme = "EXTERNAL_MANAGED"
}
