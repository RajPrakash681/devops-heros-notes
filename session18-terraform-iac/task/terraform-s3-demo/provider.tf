terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

# No credentials in here on purpose. On real AWS the provider picks them up from the
# environment / ~/.aws / an IAM role. For the emulator run they come from
# emulator_override.tf, which Terraform merges into this block.
provider "aws" {
  region = var.aws_region

  # Every taggable resource gets these tags without repeating them per resource.
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      Owner       = var.owner
      ManagedBy   = "Terraform"
    }
  }
}
