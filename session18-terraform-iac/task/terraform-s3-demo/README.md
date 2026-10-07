# Terraform S3 demo (Session 18, Task 1)

Raj Prakash, 2024EB02289. The full walkthrough, with real output and screenshots, is in
the session write-up: [`../README.md`](../README.md).

This creates one private S3 bucket the way provider v4+ expects. The bucket's settings
are separate resources, not arguments of `aws_s3_bucket`. It also uploads one object.

| File | Purpose |
|---|---|
| `provider.tf` | `terraform {}` block (Terraform `>= 1.6.0`, `hashicorp/aws ~> 6.0`) and the `aws` provider, with `default_tags` applied to every resource |
| `variables.tf` | Inputs. `environment` and `bucket_name` have `validation` rules |
| `terraform.tfvars` | Values used for the run (region `ap-south-1`, bucket `rajprakash-2024eb02289-s18-demo`) |
| `main.tf` | `aws_s3_bucket`, `aws_s3_bucket_versioning`, `aws_s3_bucket_server_side_encryption_configuration` (AES256), `aws_s3_bucket_public_access_block` (all four on), and `aws_s3_object` `hello.txt` |
| `outputs.tf` | Bucket name / ARN / region, versioning status, object URI and version ID |
| `emulator_override.tf` | **Local emulator only.** Dummy credentials and endpoints pointing at moto on `localhost:5050` |
| `.terraform.lock.hcl` | Provider version and hashes pinned by `terraform init` (v6.67.0) |
| `.gitignore` | `.terraform/`, state files, saved plans |

## Run it against the local emulator (what I did)

```bash
docker run -d --name moto -p 5050:5000 motoserver/moto:latest   # 5050: macOS uses 5000 for AirPlay

terraform init
terraform fmt -check
terraform validate
terraform plan
terraform apply -auto-approve
terraform plan            # moto drops tags sent at create time - a second apply fixes it
terraform output
terraform state list
terraform destroy -auto-approve

docker rm -f moto
```

## Run it against real AWS

1. **Delete `emulator_override.tf`.** It is the only emulator-specific file. Terraform
   merges any `*_override.tf` into the provider block, so with it gone the provider is
   back to its normal behaviour.
2. Make credentials available the usual way (`aws configure`, `AWS_PROFILE`, or an IAM role)
   and check them with `aws sts get-caller-identity`.
3. Bucket names are global across all AWS accounts. If `bucket_name` in `terraform.tfvars`
   is taken, change it.
4. Run the same `init`, `plan`, `apply`, `destroy` commands. I could not test whether the
   extra `apply` for tags is needed on real S3. The drift came from moto ignoring the tags
   inside a valid `CreateBucket` request, so I expect it is not (see the write-up).

`force_destroy = true` is set so that `destroy` can remove a versioned bucket that still
holds objects. Fine for a demo, and not something to copy onto a bucket with real data.
