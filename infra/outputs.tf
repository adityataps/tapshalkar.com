output "bucket_name" {
  description = "GCS bucket hosting the static site"
  value       = google_storage_bucket.static_site.name
}

output "artifact_registry_repo" {
  description = "Artifact Registry repository URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/tapshalkar"
}

output "backend_sa_email" {
  value = google_service_account.backend.email
}

output "graph_gen_sa_email" {
  value = google_service_account.graph_gen.email
}

output "github_actions_sa_email" {
  value = google_service_account.github_actions.email
}

output "backend_cloud_run_url" {
  description = "Cloud Run service URL (internal)"
  value       = google_cloud_run_v2_service.backend.uri
}
