variable "aws_region" {
  description = "AWS region to create the bucket in."
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Project name, used for the Project tag."
  type        = string
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "environment must be one of: dev, test, prod."
  }
}

variable "owner" {
  description = "Who owns these resources (Owner tag)."
  type        = string
}

variable "bucket_name" {
  description = "Globally unique S3 bucket name."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", var.bucket_name))
    error_message = "bucket_name must be 3-63 chars of lowercase letters, digits, dots and hyphens, starting and ending with a letter or digit."
  }
}

variable "enable_versioning" {
  description = "Turn on S3 object versioning."
  type        = bool
  default     = true
}
