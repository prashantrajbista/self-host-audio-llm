# Microsoft Foundry resource: the interviewer LLM, speech-to-text and text-to-speech as APIs, so the VM needs no
# local models. Its own region: the audio models aren't offered everywhere (eastus2 has all three).
resource "azurerm_cognitive_account" "ai" {
  name                  = "${var.prefix}-ai-${random_string.suffix.result}"
  resource_group_name   = azurerm_resource_group.main.name
  location              = var.ai_location
  kind                  = "AIServices"
  sku_name              = "S0"
  custom_subdomain_name = "${var.prefix}-ai-${random_string.suffix.result}"
}

# capacity = quota units (1 unit ~ 1K tokens/min). Created one after another: Azure rejects parallel deployments
# on the same account.
resource "azurerm_cognitive_deployment" "llm" {
  name                 = var.llm_deployment.model
  cognitive_account_id = azurerm_cognitive_account.ai.id
  model {
    format  = "OpenAI"
    name    = var.llm_deployment.model
    version = var.llm_deployment.version
  }
  sku {
    name     = "GlobalStandard"
    capacity = var.llm_deployment.capacity
  }
}

resource "azurerm_cognitive_deployment" "stt" {
  name                 = "gpt-4o-mini-transcribe"
  cognitive_account_id = azurerm_cognitive_account.ai.id
  model {
    format  = "OpenAI"
    name    = "gpt-4o-mini-transcribe"
    version = "2025-12-15"
  }
  sku {
    name     = "GlobalStandard"
    capacity = var.audio_capacity
  }
  depends_on = [azurerm_cognitive_deployment.llm]
}

resource "azurerm_cognitive_deployment" "tts" {
  name                 = "gpt-4o-mini-tts"
  cognitive_account_id = azurerm_cognitive_account.ai.id
  model {
    format  = "OpenAI"
    name    = "gpt-4o-mini-tts"
    version = "2025-12-15"
  }
  sku {
    name     = "GlobalStandard"
    capacity = var.audio_capacity
  }
  depends_on = [azurerm_cognitive_deployment.stt]
}
