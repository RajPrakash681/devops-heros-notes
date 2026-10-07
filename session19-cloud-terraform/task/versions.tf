terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

# No credentials here: on real AWS they come from the environment, ~/.aws or an IAM role.
# For the local emulator run they come from emulator_override.tf.
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      Owner       = var.owner
      Session     = "19"
      ManagedBy   = "Terraform"
    }
  }
}
