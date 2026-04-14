resource "google_model_armor_template" "chat_shield" {
  location    = var.region
  template_id = "chat-shield"

  filter_config {
    rai_settings {
      rai_filters {
        filter_type      = "HARASSMENT"
        confidence_level = "MEDIUM_AND_ABOVE"
      }
      rai_filters {
        filter_type      = "HATE_SPEECH"
        confidence_level = "MEDIUM_AND_ABOVE"
      }
      rai_filters {
        filter_type      = "SEXUALLY_EXPLICIT"
        confidence_level = "MEDIUM_AND_ABOVE"
      }
      rai_filters {
        filter_type      = "DANGEROUS_CONTENT"
        confidence_level = "MEDIUM_AND_ABOVE"
      }
    }

    pi_and_jailbreak_filter_settings {
      confidence_level = "MEDIUM_AND_ABOVE"
    }
  }
}
