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

# Document AI processor is created manually (see below) — processor type
# availability varies by location and is not reliably manageable via Terraform.
#
# To create the processor:
#   gcloud ai document-ai processor-types list --location=us --project=PROJECT_ID
# Pick a suitable type (e.g. LAYOUT_PARSER or DOCUMENT_OCR), then:
#   gcloud ai document-ai processors create \
#     --display-name=resume-parser \
#     --type=LAYOUT_PARSER \
#     --location=us \
#     --project=PROJECT_ID
# Copy the processor ID from the output and set the GitHub Actions variable:
#   DOCUMENT_AI_PROCESSOR_NAME = projects/PROJECT_ID/locations/us/processors/PROCESSOR_ID
