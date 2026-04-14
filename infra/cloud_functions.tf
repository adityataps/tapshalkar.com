# APIs required for Cloud Functions Gen2
resource "google_project_service" "cloudfunctions" {
  service            = "cloudfunctions.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloudbuild" {
  service            = "cloudbuild.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "eventarc" {
  service            = "eventarc.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "documentai" {
  service            = "documentai.googleapis.com"
  disable_on_destroy = false
}

resource "google_document_ai_processor" "resume_ocr" {
  display_name = "resume-parser"
  type         = "DOCUMENT_OCR_PROCESSOR"
  location     = "us"

  depends_on = [google_project_service.documentai]
}

# Pub/Sub topic — bridges the multi-region GCS bucket to the single-region
# Cloud Function. Eventarc can't cross that boundary directly.
resource "google_pubsub_topic" "resume_uploads" {
  name = "resume-uploads"
}

data "google_project" "project" {}

# Fetch the GCS service account for this project — used to grant Pub/Sub publish rights
data "google_storage_project_service_account" "gcs_account" {}

resource "google_pubsub_topic_iam_member" "gcs_publisher" {
  topic  = google_pubsub_topic.resume_uploads.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${data.google_storage_project_service_account.gcs_account.email_address}"
}

# Allow the Pub/Sub service agent to create OIDC tokens for the trigger SA,
# so the push subscription can authenticate to the Cloud Run endpoint.
resource "google_service_account_iam_member" "pubsub_token_creator" {
  service_account_id = google_service_account.resume_parser.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

# GCS notification — only fires for the resume PDF
resource "google_storage_notification" "resume_upload" {
  bucket             = google_storage_bucket.static_site.name
  payload_format     = "JSON_API_V1"
  topic              = google_pubsub_topic.resume_uploads.id
  event_types        = ["OBJECT_FINALIZE"]
  object_name_prefix = "Resume_Aditya_Tapshalkar"

  depends_on = [google_pubsub_topic_iam_member.gcs_publisher]
}
