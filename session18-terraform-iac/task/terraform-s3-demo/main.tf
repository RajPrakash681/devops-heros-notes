# The bucket itself. Since AWS provider v4, versioning, encryption, public access etc.
# are NOT arguments of aws_s3_bucket any more - each is its own resource below.
resource "aws_s3_bucket" "demo" {
  bucket = var.bucket_name

  # Lets `terraform destroy` empty the bucket (including old object versions) first.
  # Fine for a demo; on a bucket holding real data this should stay false.
  force_destroy = true

  tags = {
    Name = var.bucket_name
  }
}

resource "aws_s3_bucket_versioning" "demo" {
  bucket = aws_s3_bucket.demo.id

  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Suspended"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "demo" {
  bucket = aws_s3_bucket.demo.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "demo" {
  bucket                  = aws_s3_bucket.demo.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "hello" {
  bucket       = aws_s3_bucket.demo.id
  key          = "hello.txt"
  content      = "Uploaded by Terraform for ${var.owner} - Session 18.\n"
  content_type = "text/plain"

  # The object only references the bucket, so without this Terraform would upload it in
  # parallel with the versioning/encryption settings. Waiting for them means the object is
  # written into a bucket that is already versioned and encrypted by default.
  depends_on = [
    aws_s3_bucket_versioning.demo,
    aws_s3_bucket_server_side_encryption_configuration.demo,
  ]
}
