variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run resources"
  type        = string
  default     = "us-east1"
}

variable "domain" {
  description = "FQDN for the site (e.g. tapshalkar.com)"
  type        = string
}

variable "github_repo" {
  description = "GitHub repo in owner/name format (e.g. adityataps/tapshalkar.com)"
  type        = string
}

variable "graph_gen_schedule" {
  description = "Cron schedule for the graph-gen job"
  type        = string
  default     = "0 6 * * *"
}

variable "github_username" {
  description = "GitHub username for the graph-gen job"
  type        = string
  default     = "adityataps"
}

variable "certificate_domains" {
  description = "List of domains that should be added to the certificate"
  type        = list(string)
  default     = []
}

variable "steam_account_id" {
  description = "ID of the Steam Account to use"
  type        = string
  default     = ""
}

variable "steam_user_id" {
  description = "Steam 64-bit user ID for the graph-gen job"
  type        = string
}
