output "bucket_name" {
  description = "GCS bucket hosting the static site"
  value       = google_storage_bucket.static_site.name
}

output "artifact_registry_repo" {
  description = "Artifact Registry repository URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/tapshalkar"
}
