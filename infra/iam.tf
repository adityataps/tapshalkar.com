# Service account for the FastAPI Cloud Run service
resource "google_service_account" "backend" {
  account_id   = "backend-sa"
  display_name = "Backend Cloud Run Service Account"
}

# Service account for the graph-gen Cloud Run Job
resource "google_service_account" "graph_gen" {
  account_id   = "graph-gen-sa"
  display_name = "Graph Gen Job Service Account"
}

# Service account for GitHub Actions (WIF)
resource "google_service_account" "github_actions" {
  account_id   = "github-actions-sa"
  display_name = "GitHub Actions Service Account"
}

# Backend SA: read GCS objects
resource "google_project_iam_member" "backend_gcs_reader" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

# Graph-gen SA: write GCS objects
resource "google_project_iam_member" "graph_gen_gcs_writer" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.graph_gen.email}"
}

# GitHub Actions SA: deploy Cloud Run
resource "google_project_iam_member" "github_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# GitHub Actions SA: push Artifact Registry images
resource "google_project_iam_member" "github_ar_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# GitHub Actions SA: deploy to GCS (frontend)
resource "google_project_iam_member" "github_gcs_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# GitHub Actions SA: act as other SAs (required for Cloud Run deploy)
resource "google_project_iam_member" "github_sa_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# GitHub Actions SA: invalidate CDN cache
resource "google_project_iam_member" "github_compute_admin" {
  project = var.project_id
  role    = "roles/compute.networkAdmin"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}
