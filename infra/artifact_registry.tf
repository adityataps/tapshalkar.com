resource "google_artifact_registry_repository" "tapshalkar" {
  location      = var.region
  repository_id = "tapshalkar"
  format        = "DOCKER"
  description   = "Docker images for tapshalkar.com services"
}
