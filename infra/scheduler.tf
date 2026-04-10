resource "google_cloud_scheduler_job" "graph_gen" {
  name      = "graph-gen-daily"
  region    = var.region
  schedule  = var.graph_gen_schedule
  time_zone = "UTC"

  http_target {
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${google_cloud_run_v2_job.graph_gen.name}:run"
    http_method = "POST"

    oauth_token {
      service_account_email = google_service_account.graph_gen.email
    }
  }
}
