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
  EOT
}
