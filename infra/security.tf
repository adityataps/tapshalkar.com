resource "google_compute_security_policy" "backend" {
  name        = "tapshalkar-backend-policy"
  description = "Rate limiting for the Cloud Run backend service"

  # Rate-limit all callers to 10 req/min per IP, ban for 5 minutes on breach.
  # Matches the slowapi limit in the application layer.
  rule {
    priority    = 100
    action      = "rate_based_ban"
    description = "10 req/min per IP; ban 5 min on breach"

    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }

    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      enforce_on_key = "IP"

      rate_limit_threshold {
        count        = 10
        interval_sec = 60
      }

      ban_duration_sec = 300
    }
  }

  # Default allow
  rule {
    priority    = 2147483647
    action      = "allow"
    description = "Default allow"

    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
  }
}
