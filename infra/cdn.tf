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

# Managed TLS cert
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

# HTTPS proxy
resource "google_compute_target_https_proxy" "default" {
  name             = "tapshalkar-https-proxy"
  url_map          = google_compute_url_map.default.id
  ssl_certificates = [google_compute_managed_ssl_certificate.default.id]
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
