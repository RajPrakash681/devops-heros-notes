variable "aws_region" {
  description = "AWS region for every resource in this project."
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Prefix for resource names and the Project tag."
  type        = string
  default     = "session19"
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
  description = "Owner tag value."
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC."
  type        = string
  default     = "10.20.0.0/16"

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "vpc_cidr must be a valid IPv4 CIDR block, e.g. 10.20.0.0/16."
  }
}

variable "public_subnet_cidr" {
  description = "CIDR block of the public subnet. Must sit inside vpc_cidr."
  type        = string
  default     = "10.20.1.0/24"

  validation {
    condition     = can(cidrhost(var.public_subnet_cidr, 0))
    error_message = "public_subnet_cidr must be a valid IPv4 CIDR block, e.g. 10.20.1.0/24."
  }
}

variable "ssh_allowed_cidr" {
  description = "The only source range allowed to reach port 22. Use your own IP as a /32."
  type        = string

  validation {
    condition     = can(cidrhost(var.ssh_allowed_cidr, 0)) && var.ssh_allowed_cidr != "0.0.0.0/0"
    error_message = "ssh_allowed_cidr must be a valid CIDR and must not be 0.0.0.0/0 - do not open SSH to the whole internet."
  }
}

variable "instance_type" {
  description = "EC2 instance type. Limited to small types so a typo cannot get expensive."
  type        = string
  default     = "t3.micro"

  validation {
    condition     = contains(["t2.micro", "t3.micro", "t3.small"], var.instance_type)
    error_message = "instance_type must be one of: t2.micro, t3.micro, t3.small."
  }
}

variable "instance_name" {
  description = "Name tag of the web server."
  type        = string
  default     = "session19-web"
}

variable "bucket_name" {
  description = "Globally unique name of the S3 bucket for the app's assets."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", var.bucket_name))
    error_message = "bucket_name must be 3-63 chars of lowercase letters, digits, dots and hyphens."
  }
}
