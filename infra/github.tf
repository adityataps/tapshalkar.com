locals {
  github_repo_name = split("/", var.github_repo)[1]
}

import {
  to = github_actions_variable.gcp_project_id
  id = "tapshalkar.com:GCP_PROJECT_ID"
}

import {
  to = github_actions_variable.gcp_region
  id = "tapshalkar.com:GCP_REGION"
}

import {
  to = github_actions_variable.wif_provider
  id = "tapshalkar.com:WIF_PROVIDER"
}

import {
  to = github_actions_variable.wif_service_account
  id = "tapshalkar.com:WIF_SERVICE_ACCOUNT"
}

import {
  to = github_actions_variable.gcs_bucket
  id = "tapshalkar.com:GCS_BUCKET"
}

import {
  to = github_actions_variable.backend_image
  id = "tapshalkar.com:BACKEND_IMAGE"
}

import {
  to = github_actions_variable.job_image
  id = "tapshalkar.com:JOB_IMAGE"
}

import {
  to = github_actions_variable.cdn_url_map
  id = "tapshalkar.com:CDN_URL_MAP"
}

import {
  to = github_actions_variable.resume_parser_sa
  id = "tapshalkar.com:RESUME_PARSER_SA"
}

import {
  to = github_actions_variable.resume_uploads_topic
  id = "tapshalkar.com:RESUME_UPLOADS_TOPIC"
}

import {
  to = github_actions_variable.document_ai_processor_name
  id = "tapshalkar.com:DOCUMENT_AI_PROCESSOR_NAME"
}

resource "github_actions_variable" "gcp_project_id" {
  repository    = local.github_repo_name
  variable_name = "GCP_PROJECT_ID"
  value         = var.project_id
}

resource "github_actions_variable" "gcp_region" {
  repository    = local.github_repo_name
  variable_name = "GCP_REGION"
  value         = var.region
}

resource "github_actions_variable" "wif_provider" {
  repository    = local.github_repo_name
  variable_name = "WIF_PROVIDER"
  value         = google_iam_workload_identity_pool_provider.github.name
}

resource "github_actions_variable" "wif_service_account" {
  repository    = local.github_repo_name
  variable_name = "WIF_SERVICE_ACCOUNT"
  value         = google_service_account.github_actions.email
}

resource "github_actions_variable" "gcs_bucket" {
  repository    = local.github_repo_name
  variable_name = "GCS_BUCKET"
  value         = google_storage_bucket.static_site.name
}

resource "github_actions_variable" "backend_image" {
  repository    = local.github_repo_name
  variable_name = "BACKEND_IMAGE"
  value         = "${var.region}-docker.pkg.dev/${var.project_id}/tapshalkar/backend"
}

resource "github_actions_variable" "job_image" {
  repository    = local.github_repo_name
  variable_name = "JOB_IMAGE"
  value         = "${var.region}-docker.pkg.dev/${var.project_id}/tapshalkar/graph-gen"
}

resource "github_actions_variable" "cdn_url_map" {
  repository    = local.github_repo_name
  variable_name = "CDN_URL_MAP"
  value         = google_compute_url_map.default.name
}

resource "github_actions_variable" "resume_parser_sa" {
  repository    = local.github_repo_name
  variable_name = "RESUME_PARSER_SA"
  value         = google_service_account.resume_parser.email
}

resource "github_actions_variable" "resume_uploads_topic" {
  repository    = local.github_repo_name
  variable_name = "RESUME_UPLOADS_TOPIC"
  value         = google_pubsub_topic.resume_uploads.name
}

resource "github_actions_variable" "document_ai_processor_name" {
  repository    = local.github_repo_name
  variable_name = "DOCUMENT_AI_PROCESSOR_NAME"
  value         = google_document_ai_processor.resume_ocr.id
}
