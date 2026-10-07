# LOCAL EMULATOR ONLY - delete this file to target real AWS.
#
# Terraform merges any *_override.tf file into the matching block of the main config.
# This one adds dummy credentials and sends the EC2, S3 and STS API calls to a moto
# server running in Docker:
#
#   docker run -d --name moto -p 5050:5000 motoserver/moto:latest
#
# (Host port 5050, not 5000: on macOS, port 5000 is taken by AirPlay Receiver.)
provider "aws" {
  access_key = "test"
  secret_key = "test"

  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true
  s3_use_path_style           = true

  endpoints {
    ec2 = "http://localhost:5050"
    s3  = "http://localhost:5050"
    sts = "http://localhost:5050"
  }
}
