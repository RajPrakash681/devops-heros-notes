resource "aws_s3_bucket" "assets" {
  bucket = var.bucket_name

  # Demo only: lets `terraform destroy` delete the bucket even if it has objects in it.
  force_destroy = true

  tags = {
    Name = var.bucket_name
  }
}

resource "aws_s3_bucket_public_access_block" "assets" {
  bucket = aws_s3_bucket.assets.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
