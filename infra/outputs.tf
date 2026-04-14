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

output "lb_ip" {
  description = "Load balancer IP — point your DNS A record here"
  value       = google_compute_global_address.default.address
}

output "wif_provider" {
  description = "WIF provider resource name — used in GitHub Actions workflows"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "resume_parser_sa_email" {
  description = "resume-parser Cloud Function service account — set as RESUME_PARSER_SA GitHub Actions variable"
  value       = google_service_account.resume_parser.email
}

output "document_ai_processor_name" {
  description = "Full Document AI processor resource name — set as DOCUMENT_AI_PROCESSOR_NAME GitHub Actions variable"
  value       = "projects/${var.project_id}/locations/us/processors/${google_document_ai_processor.resume_ocr.id}"
}
