variable "prefix" {
  description = "Name prefix for every resource; lowercase letters/digits only (storage account naming rules)"
  type        = string
  default     = "interview"
}

variable "location" {
  description = "Azure region; free-trial subscriptions may be refused Postgres in some regions (try eastus2 / centralus)"
  type        = string
  default     = "eastus"
}

variable "vm_size" {
  description = "4 vCPU / 16 GiB, CPU only"
  type        = string
  default     = "Standard_D4as_v5"
}

variable "db_sku" {
  description = "Burstable, 2 vCore / 4 GiB"
  type        = string
  default     = "B_Standard_B2s"
}

variable "admin_username" {
  type    = string
  default = "azureuser"
}

variable "ssh_public_key_path" {
  description = "Your own key, for logging in"
  type        = string
  default     = "~/.ssh/interview_vm.pub"
}

variable "deploy_public_key_path" {
  description = "GitHub Actions deploy key (its private half is the VM_SSH_KEY repository secret)"
  type        = string
  default     = "~/.ssh/interview_deploy.pub"
}

variable "ssh_allowed_cidr" {
  description = "Who may reach port 22. GitHub-hosted runners have changing IPs, so * with key-only login"
  type        = string
  default     = "*"
}

variable "storage_container" {
  description = "Must match STORAGE_BUCKET in .env.production"
  type        = string
  default     = "interview-coach"
}

variable "budget_email" {
  description = "Gets the 80% / 100% budget alerts"
  type        = string
}

variable "budget_amount" {
  description = "Monthly budget in USD for the resource group"
  type        = number
  default     = 180
}
