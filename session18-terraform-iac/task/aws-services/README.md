# Session 18 — AWS Services — Research Notes (Task 2)

- **Name:** Raj Prakash
- **Enrollment No:** 2024EB02289

---

These are my research notes for Session 18, Task 2 (AWS Services Research): one folder per
service, each covering the topics the assignment lists, plus the gotchas and the "why"
behind them, a Terraform snippet (AWS provider `~> 6.0`), a few `aws` CLI commands, key
takeaways and links to the official AWS documentation. I have no AWS credentials on this
machine, so none of the CLI or Terraform was run. Those blocks are reference examples
checked against the docs, not transcripts of real output.

| # | Service | Category | Summary |
|---|---|---|---|
| 01 | [IAM](01-iam/README.md) | Governance | Users, groups, roles and policies; how a request is evaluated (explicit Deny > Allow > implicit deny) and why roles beat access keys |
| 02 | [EC2](02-ec2/README.md) | Compute | AMIs, instance types, key pairs, security groups, EBS, public vs private IPs, and what stop / hibernate / terminate actually do |
| 03 | [S3](03-s3/README.md) | Storage | Buckets and objects, storage classes, versioning, lifecycle rules, default encryption, bucket policies and Block Public Access |
| 04 | [VPC](04-vpc/README.md) | Networking | CIDR planning, subnets and route tables, IGW vs NAT gateway (free vs per-hour + per-GB), security groups vs NACLs |
| 05 | [DynamoDB & RDS](05-dynamodb-rds/README.md) | Database | DynamoDB keys and hot partitions; RDS engines, backups, Multi-AZ vs read replicas; when to pick which |
