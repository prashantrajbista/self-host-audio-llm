resource "azurerm_linux_virtual_machine" "main" {
  name                            = "${var.prefix}-vm"
  resource_group_name             = azurerm_resource_group.main.name
  location                        = azurerm_resource_group.main.location
  size                            = var.vm_size
  admin_username                  = var.admin_username
  disable_password_authentication = true
  network_interface_ids           = [azurerm_network_interface.main.id]

  admin_ssh_key {
    username   = var.admin_username
    public_key = file(pathexpand(var.ssh_public_key_path))
  }

  admin_ssh_key {
    username   = var.admin_username
    public_key = file(pathexpand(var.deploy_public_key_path))
  }

  # Docker images + model cache + logs
  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "StandardSSD_LRS"
    disk_size_gb         = 256
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  # runs once on first boot; editing cloud-init.yaml later replaces the VM
  custom_data = base64encode(templatefile("${path.module}/cloud-init.yaml", { admin_username = var.admin_username }))
}
