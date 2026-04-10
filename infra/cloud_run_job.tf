resource "google_cloud_run_v2_job" "graph_gen" {
  name     = "graph-gen"
  location = var.region

  template {
    template {
      service_account = google_service_account.graph_gen.email

      timeout = "600s"

      containers {
        image = "us-docker.pkg.dev/cloudrun/container/hello" # placeholder

        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }

        env {
          name  = "GCS_BUCKET"
          value = google_storage_bucket.static_site.name
        }

        env {
          name  = "GITHUB_USERNAME"
          value = var.github_username
        }

        env {
          name  = "STEAM_USER_ID"
          value = var.steam_user_id
        }

        dynamic "env" {
          for_each = {
            "ANTHROPIC_API_KEY"     = "anthropic-api-key"
            "SPOTIFY_CLIENT_ID"     = "spotify-client-id"
            "SPOTIFY_CLIENT_SECRET" = "spotify-client-secret"
            "SPOTIFY_REFRESH_TOKEN" = "spotify-refresh-token"
            "STEAM_API_KEY"         = "steam-api-key"
            "GITHUB_TOKEN"          = "github-token"
          }
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = google_secret_manager_secret.secrets[env.value].secret_id
                version = "latest"
              }
            }
          }
        }

        env {
          name  = "STEAM_USER_ID"
          value = var.steam_account_id
        }
      }
    }
  }

  depends_on = [
    google_secret_manager_secret_iam_member.graph_gen_secrets
  ]

  # lifecycle {
  #   ignore_changes = [template[0].template[0].containers[0].image]
  # }
}
