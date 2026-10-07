# Session 18 — AWS Services — 03: S3 (Storage)

- **Name:** Raj Prakash
- **Enrollment No:** 24BCS10328

---

> Research notes for Session 18, Task 2. No AWS credentials on this machine, so nothing
> below was run. CLI and Terraform blocks are reference examples, not transcripts. (The
> class demo in [`terraform-s3-demo`](../../../terraform-s3-demo/) is the hands-on
> counterpart.)

## What is S3?

Amazon Simple Storage Service (S3) is **object storage**: you store whole objects (bytes plus
metadata) under a key, and read or replace them whole over an HTTPS API. It is not a
filesystem and not a block device. You can't append to an object or edit byte 500 in place;
you upload a new version of the whole thing.

What makes it the default place to put things in AWS:

- Designed for **11 nines (99.999999999%) of durability**; data in most classes is stored
  across multiple Availability Zones.
- Effectively unlimited capacity; you pay for what you store, the requests, and data
  transferred out.
- **Strong read-after-write consistency** for all object operations since December 2020. A
  successful `PUT` or `DELETE` is immediately visible to a following `GET` or `LIST`. Before
  that, overwrites and deletes were only eventually consistent, and a lot of old blog posts
  still warn about it.

## Buckets

A bucket is the top-level container. It belongs to one **region**, but its **name is
globally unique** across all AWS accounts, which is why `my-bucket` is always taken.

- Names: 3–63 characters, lowercase letters, numbers, hyphens (and dots, which I'd avoid
  because they break virtual-hosted-style HTTPS certificates).
- Settings live on the bucket: versioning, encryption defaults, lifecycle rules, policies,
  Block Public Access, logging, replication.
- A bucket must be **empty** (including every old version and delete marker) before it can
  be deleted. This is why `terraform destroy` fails on a non-empty (or versioned) bucket unless
  you set `force_destroy = true`.

**Secure by default (since April 2023):** new buckets have **Block Public Access turned on**
and **ACLs disabled** (Object Ownership = *Bucket owner enforced*). Making something public
is now a deliberate act, not an accident.

## Objects

An object is the data plus:

| Part | Notes |
|---|---|
| **Key** | The full name, e.g. `reports/2026/q3.csv`. The namespace is flat |
| **Value** | The bytes. From zero bytes up to tens of terabytes (the documented limit is now 50 TB; for years it was 5 TB) |
| **Version ID** | Set when versioning is enabled |
| **Metadata** | System (`Content-Type`, size, ...) and user-defined (`x-amz-meta-*`) |
| **Tags** | Key/value pairs usable in lifecycle rules and IAM conditions |

**There are no folders.** `reports/2026/` is just a common key prefix; the console draws
folders to be friendly. Prefixes still matter for performance: S3 scales request rates per
prefix (thousands of requests per second per prefix), so spreading heavy traffic across
prefixes helps.

**Uploads:** a single `PUT` can be up to 5 GB. Anything bigger has to use **multipart
upload**, which is recommended well before that (the AWS CLI switches to it automatically).

## Storage classes

All classes have the same durability design; they differ in availability, retrieval speed,
minimum charges and price per GB.

| Class | AZs | Min. storage duration | Retrieval | Good for |
|---|---|---|---|---|
| S3 Standard | 3+ | None | Milliseconds | Hot data, websites, active datasets |
| S3 Intelligent-Tiering | 3+ | None | Milliseconds (optional archive tiers are slower) | Unknown or changing access patterns; small per-object monitoring fee |
| S3 Standard-IA | 3+ | 30 days | Milliseconds, per-GB retrieval fee | Backups needed quickly but rarely |
| S3 One Zone-IA | 1 | 30 days | Milliseconds, per-GB retrieval fee | Re-creatable data (thumbnails, secondary copies) |
| S3 Glacier Instant Retrieval | 3+ | 90 days | Milliseconds, higher retrieval fee | Archives read about once a quarter |
| S3 Glacier Flexible Retrieval | 3+ | 90 days | Minutes to hours, **restore first** | Backups, DR copies |
| S3 Glacier Deep Archive | 3+ | 180 days | Hours, **restore first** | Compliance archives kept for years |

There is also **S3 Express One Zone** for very low latency in a single AZ (it uses a
different bucket type, "directory buckets").

Cost gotchas:

- **Minimum duration**: delete an object from Standard-IA after 5 days and you still pay
  for 30.
- **Minimum billable size**: IA classes and Glacier Instant Retrieval bill small objects as
  if they were 128 KB. Millions of tiny files in IA can cost *more* than Standard.
- **Glacier Flexible / Deep Archive objects aren't readable directly.** You request a
  restore and wait, then read the temporary copy.

## Versioning

A bucket is in one of three states: **unversioned** (the default), **versioning-enabled**,
or **versioning-suspended**. Once enabled, it can never go back to unversioned, only
suspended.

With versioning on:

- Every overwrite creates a **new version**; the old one is kept.
- A plain `DELETE` doesn't delete anything. It adds a **delete marker** on top, so the
  object "disappears" but every version is still there (and still billed). Removing the
  delete marker brings it back.
- Deleting a specific version ID is the only permanent delete.

That's the safety net against accidental deletes and overwrites (and the reason Terraform
state buckets should always be versioned). The flip side is cost: without a lifecycle rule,
**old versions pile up forever**. Versioning is also a prerequisite for replication and
Object Lock.

## Lifecycle policies

Lifecycle rules automate "move it, then delete it" for objects matched by prefix, tags or
size:

| Action | Example |
|---|---|
| Transition current versions | To Standard-IA after 30 days, Glacier Flexible after 90 |
| Expire current versions | Delete logs after 365 days (adds a delete marker if versioned) |
| Transition / expire **noncurrent** versions | Permanently delete old versions 30 days after they're replaced |
| Remove expired delete markers | Clean up markers with no versions behind them |
| Abort incomplete multipart uploads | Delete orphaned upload parts after 7 days |

Things to know:

- **Incomplete multipart uploads** are invisible in normal listings but billed as storage.
  An abort rule on every bucket is cheap insurance.
- Lifecycle runs **asynchronously** (roughly daily), so expect some delay.
- Transitions cost per request, and since September 2024 lifecycle by default **doesn't
  transition objects smaller than 128 KB**, because for tiny objects the transition fees
  outweigh any storage savings.
- Objects must sit in Standard for at least 30 days before lifecycle can move them to
  Standard-IA or One Zone-IA.

## Encryption

**Since January 2023, every new object is encrypted at rest by default** with SSE-S3. You
can't upload an unencrypted object any more; the choice is only *which* encryption.

| Option | Who manages the key | When to use |
|---|---|---|
| SSE-S3 | S3 (AES-256) | The default; fine for most data |
| SSE-KMS | AWS KMS key (AWS managed or your own) | Need key-level access control, CloudTrail audit of key use, or key rotation policies |
| DSSE-KMS | KMS, two layers of encryption | Compliance regimes that require dual-layer |
| SSE-C | You send the key with each request | Rare; you must manage and supply keys yourself |
| Client-side | You, before upload | Data must never reach AWS in plaintext |

With SSE-KMS, every request can call KMS, which costs money and counts against KMS request
quotas. Enabling **S3 Bucket Keys** cuts those KMS calls dramatically. Also remember that
with SSE-KMS a reader needs **`kms:Decrypt` on the key as well as `s3:GetObject`**; a
missing KMS permission looks like an S3 `AccessDenied`.

In transit: enforce TLS with a bucket policy (below).

## Bucket policies

A bucket policy is a **resource-based** IAM policy on the bucket, so it has a `Principal`.
It's how you grant cross-account access, service access (CloudFront, ALB logs), or add
blanket denies.

Realistic example: a private bucket behind CloudFront (Origin Access Control). Only the one
CloudFront distribution can read objects, and any non-HTTPS request is denied:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCloudFrontReadOnly",
      "Effect": "Allow",
      "Principal": { "Service": "cloudfront.amazonaws.com" },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::raj-demo-site/*",
      "Condition": {
        "StringEquals": {
          "AWS:SourceArn": "arn:aws:cloudfront::123456789012:distribution/EDFDVBD6EXAMPLE"
        }
      }
    },
    {
      "Sid": "DenyInsecureTransport",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::raj-demo-site",
        "arn:aws:s3:::raj-demo-site/*"
      ],
      "Condition": {
        "Bool": { "aws:SecureTransport": "false" }
      }
    }
  ]
}
```

How it fits with the rest:

- **IAM policy vs bucket policy**: within one account, an allow in either is usually enough.
  Cross-account, both must allow. An explicit deny in either wins.
- **Block Public Access overrides bucket policies.** With BPA on, a policy granting
  `"Principal": "*"` read access is rejected or ignored. That's the point.
- **You can lock yourself out.** A broad `Deny` (e.g. "deny unless from this VPC endpoint")
  applies to admins too. The account root user can still delete the bucket policy to
  recover.
- The S3 static-website endpoint is **HTTP only**; put CloudFront in front for HTTPS.

## Common use cases

- **Terraform remote state** (directly relevant to this session): a versioned, encrypted,
  private bucket. Recent Terraform versions can lock state with a lock file in the bucket
  itself (`use_lockfile = true`), so a separate DynamoDB lock table is no longer needed.
- **Static websites and assets** behind CloudFront.
- **Backups and archives**, moved to Glacier classes by lifecycle.
- **Log storage**: ALB, CloudFront and CloudTrail logs all land in S3.
- **Data lakes**: Athena, EMR and Glue query data in place.
- **Artifact storage** for CI pipelines; **presigned URLs** for time-limited uploads and
  downloads without making anything public.

```hcl
terraform {
  backend "s3" {
    bucket       = "raj-tfstate-ap-south-1"
    key          = "session18/terraform.tfstate"
    region       = "ap-south-1"
    encrypt      = true
    use_lockfile = true
  }
}
```

## Terraform example (for reference)

Since AWS provider v4, bucket settings are **separate resources** rather than blocks inside
`aws_s3_bucket`. In provider `~> 6.0`:

```hcl
resource "aws_s3_bucket" "reports" {
  bucket = "raj-demo-reports"
}

resource "aws_s3_bucket_versioning" "reports" {
  bucket = aws_s3_bucket.reports.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "reports" {
  bucket = aws_s3_bucket.reports.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "reports" {
  bucket                  = aws_s3_bucket.reports.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "reports" {
  bucket = aws_s3_bucket.reports.id

  rule {
    id     = "reports-tiering"
    status = "Enabled"

    filter {
      prefix = "reports/"
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}
```

## Commands worth knowing

Reference only; not run on this machine. `aws s3` is the high-level, `cp`/`sync`-style
interface; `aws s3api` maps one-to-one onto the API.

```bash
aws s3 ls                                     # buckets
aws s3 ls s3://raj-demo-reports/reports/      # objects under a prefix
aws s3 cp q3.csv s3://raj-demo-reports/reports/2026/q3.csv
aws s3 sync ./site s3://raj-demo-site --delete   # --delete removes remote files missing locally

aws s3api put-bucket-versioning --bucket raj-demo-reports \
  --versioning-configuration Status=Enabled
aws s3api list-object-versions --bucket raj-demo-reports --prefix reports/2026/
aws s3api get-public-access-block --bucket raj-demo-reports
aws s3api get-bucket-encryption --bucket raj-demo-reports

# Time-limited download link. Max 7 days, and never longer than the signing
# credentials live (a role session's link dies when the session does).
aws s3 presign s3://raj-demo-reports/reports/2026/q3.csv --expires-in 3600
```

## Key takeaways

- S3 is object storage: flat namespace, whole-object writes, strongly consistent since
  December 2020.
- New buckets are private by default (Block Public Access on, ACLs off), and every new
  object is encrypted by default.
- Pick storage classes by access pattern, and mind the minimum-duration and
  minimum-size charges.
- Versioning turns deletes into delete markers; pair it with lifecycle rules for
  noncurrent versions and incomplete multipart uploads, or costs creep up.
- Bucket policies are resource-based policies: explicit deny wins, cross-account needs
  both sides, and Block Public Access overrides public grants.

## References

- What is Amazon S3? — https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html
- Storage classes — https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html
- Versioning — https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html
- Managing the lifecycle of objects — https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html
- Protecting data with encryption — https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingEncryption.html
- Default bucket encryption — https://docs.aws.amazon.com/AmazonS3/latest/userguide/default-bucket-encryption.html
- Bucket policies — https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-policies.html
- Blocking public access — https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html
