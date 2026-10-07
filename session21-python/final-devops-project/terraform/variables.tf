variable "aws_region" {
  type    = string
  default = "ap-south-1"
}

variable "cluster_name" {
  type    = string
  default = "taskboard-eks"
}

variable "environment" {
  type    = string
  default = "dev"
}
