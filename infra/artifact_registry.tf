resource "google_artifact_registry_repository" "tapshalkar" {
  location      = var.region
  repository_id = "tapshalkar"
  format        = "DOCKER"
  description   = "Docker images for tapshalkar.com services"

  cleanup_policy_dry_run = false

  cleanup_policies {
    id     = "keep-last-5"
    action = "KEEP"
    most_recent_versions {
      keep_count = 5
    }
  }

  cleanup_policies {
    id     = "delete-old"
    action = "DELETE"
    condition {
      older_than = "0s"
    }
  }
}
