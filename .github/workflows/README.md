# GitHub Actions — Required Repository Variables & Secrets

Configure these in **GitHub → Settings → Secrets and variables → Actions**.

## Repository Variables

| Variable | Value |
|---|---|
| `GCP_PROJECT_ID` | GCP project ID |
| `GCP_REGION` | `us-central1` |
| `GCS_BUCKET` | value from `terraform output -raw bucket_name` |
| `WIF_PROVIDER` | value from `terraform output -raw wif_provider` |
| `WIF_SERVICE_ACCOUNT` | value from `terraform output -raw github_actions_sa_email` |
| `BACKEND_IMAGE` | `us-central1-docker.pkg.dev/YOUR_PROJECT/tapshalkar/backend` |
| `JOB_IMAGE` | `us-central1-docker.pkg.dev/YOUR_PROJECT/tapshalkar/graph-gen` |
| `CDN_URL_MAP` | `tapshalkar-url-map` |

## Repository Secrets

| Secret | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `GITHUB_TOKEN` | Auto-provided by GitHub Actions |
| `SPOTIFY_CLIENT_ID` | Spotify app client ID |
| `SPOTIFY_CLIENT_SECRET` | Spotify app client secret |
| `SPOTIFY_REFRESH_TOKEN` | Spotify refresh token |
| `STEAM_API_KEY` | Steam web API key |
| `STEAM_USER_ID` | Steam user ID |
| `RESEND_API_KEY` | Resend API key |
