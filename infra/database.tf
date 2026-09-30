# letters and digits only, so it drops into DATABASE_URL without URL-encoding
resource "random_password" "db" {
  length  = 32
  special = false
}

resource "azurerm_postgresql_flexible_server" "main" {
  name                          = "${var.prefix}-pg-${random_string.suffix.result}"
  resource_group_name           = azurerm_resource_group.main.name
  location                      = azurerm_resource_group.main.location
  version                       = "16"
  sku_name                      = var.db_sku
  storage_mb                    = 32768
  backup_retention_days         = 7
  administrator_login           = "appadmin"
  administrator_password        = random_password.db.result
  public_network_access_enabled = true

  lifecycle {
    ignore_changes = [zone] # Azure picks one; don't fight it on later plans
  }
}

resource "azurerm_postgresql_flexible_server_database" "app" {
  name      = "app"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# only the VM may connect
resource "azurerm_postgresql_flexible_server_firewall_rule" "vm" {
  name             = "vm"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = azurerm_public_ip.main.ip_address
  end_ip_address   = azurerm_public_ip.main.ip_address
}
