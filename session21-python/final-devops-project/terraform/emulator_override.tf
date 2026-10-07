# LOCAL EMULATOR ONLY - delete this file to target real AWS.
#
# Terraform merges any *_override.tf file into the matching block of the main config.
# This one adds dummy credentials and sends every AWS API call the VPC and EKS modules
# make to a moto server running in Docker:
#
#   docker run -d --name moto -p 5050:5000 -e MOTO_IAM_LOAD_MANAGED_POLICIES=true motoserver/moto:latest
#
# (Host port 5050, not 5000: on macOS, port 5000 is taken by AirPlay Receiver.
# MOTO_IAM_LOAD_MANAGED_POLICIES makes moto preload the AWS managed policies such as
# AmazonEKSClusterPolicy; without it every policy attachment in the EKS module fails.)
provider "aws" {
  access_key = "test"
  secret_key = "test"

  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true
  s3_use_path_style           = true

  endpoints {
    ec2         = "http://localhost:5050"
    sts         = "http://localhost:5050"
    iam         = "http://localhost:5050"
    eks         = "http://localhost:5050"
    kms         = "http://localhost:5050"
    logs        = "http://localhost:5050"
    ssm         = "http://localhost:5050"
    autoscaling = "http://localhost:5050"
  }
}
