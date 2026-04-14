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
  type         = "LAYOUT_PARSER_PROCESSOR"
  location     = "us"

  depends_on = [google_project_service.documentai]
}
