terraform {
  required_version = ">= 1.6"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
  # state stays local (infra/terraform.tfstate, gitignored): it contains the DB password and storage keys
}

# subscription comes from ARM_SUBSCRIPTION_ID (see README "Provision Azure with Terraform")
provider "azurerm" {
  features {}
}
