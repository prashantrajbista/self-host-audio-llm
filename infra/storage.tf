# storage account and Postgres names are globally unique
resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

resource "azurerm_storage_account" "main" {
  name                            = "${var.prefix}${random_string.suffix.result}"
  resource_group_name             = azurerm_resource_group.main.name
  location                        = azurerm_resource_group.main.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
}

# CVs and recordings; browsers read them only through short-lived SAS links
resource "azurerm_storage_container" "files" {
  name                  = var.storage_container
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}
