output "vm_ip" {
  description = "Point the DNS A records here"
  value       = azurerm_public_ip.main.ip_address
}

output "ssh_command" {
  value = "ssh -i ~/.ssh/interview_vm ${var.admin_username}@${azurerm_public_ip.main.ip_address}"
}

# appended to your own .env.production before it is copied to the VM
output "azure_env" {
  sensitive = true
  value     = <<-EOT
    DATABASE_URL=postgresql+asyncpg://${azurerm_postgresql_flexible_server.main.administrator_login}:${random_password.db.result}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/${azurerm_postgresql_flexible_server_database.app.name}?ssl=require
    AZURE_STORAGE_CONNECTION_STRING=${azurerm_storage_account.main.primary_connection_string}
    LLM_ENDPOINT=https://${azurerm_cognitive_account.ai.custom_subdomain_name}.openai.azure.com/openai
    STT_ENDPOINT=https://${azurerm_cognitive_account.ai.custom_subdomain_name}.openai.azure.com/openai
    TTS_ENDPOINT=https://${azurerm_cognitive_account.ai.custom_subdomain_name}.openai.azure.com/openai
    LLM_MODEL=${azurerm_cognitive_deployment.llm.name}
    STT_MODEL=${azurerm_cognitive_deployment.stt.name}
    TTS_MODEL=${azurerm_cognitive_deployment.tts.name}
    OPENAI_API_KEY=${azurerm_cognitive_account.ai.primary_access_key}
  EOT
}
