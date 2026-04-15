locals {
  secret_ids = [
    "anthropic-api-key",
    "voyage-api-key",
    "spotify-client-id",
    "spotify-client-secret",
    "spotify-refresh-token",
    "steam-api-key",
    "github-token",
    "resend-api-key",
    "trakt-client-id",
    "trakt-client-secret",
    "trakt-refresh-token",
  ]
}

resource "google_secret_manager_secret" "secrets" {
  for_each  = toset(local.secret_ids)
  secret_id = each.key

  replication {
    auto {}
  }
}

# Allow backend SA to access its secrets
resource "google_secret_manager_secret_iam_member" "backend_secrets" {
  for_each  = toset(["anthropic-api-key", "resend-api-key", "voyage-api-key"])
  secret_id = google_secret_manager_secret.secrets[each.key].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend.email}"
}

# Allow graph-gen SA to access its secrets
resource "google_secret_manager_secret_iam_member" "graph_gen_secrets" {
  for_each = toset([
    "anthropic-api-key",
    "voyage-api-key",
    "spotify-client-id",
    "spotify-client-secret",
    "spotify-refresh-token",
    "steam-api-key",
    "github-token",
    "trakt-client-id",
    "trakt-client-secret",
    "trakt-refresh-token",
  ])
  secret_id = google_secret_manager_secret.secrets[each.key].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.graph_gen.email}"
}
