data "cloudflare_zone" "this" {
  name = var.domain
}

# Apex A record → GCP load balancer IP
resource "cloudflare_record" "apex" {
  zone_id = data.cloudflare_zone.this.id
  name    = "@"
  content = google_compute_global_address.default.address
  type    = "A"
  proxied = true
  ttl     = 1
}

# www CNAME → apex; the GCP URL map redirects www → aditya.tapshalkar.com
resource "cloudflare_record" "www" {
  zone_id = data.cloudflare_zone.this.id
  name    = "www"
  content = var.domain
  type    = "CNAME"
  proxied = true
  ttl     = 1
}

# Primary subdomain A record → GCP load balancer IP
resource "cloudflare_record" "subdomain" {
  zone_id = data.cloudflare_zone.this.id
  name    = var.subdomain
  content = google_compute_global_address.default.address
  type    = "A"
  proxied = true
  ttl     = 1
}
