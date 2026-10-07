# Session 18 — AWS Services — 02: EC2 (Compute)

- **Name:** Raj Prakash
- **Enrollment No:** 2024EB02289

---

> Research notes for Session 18, Task 2. No AWS credentials on this machine, so nothing
> below was run. CLI and Terraform blocks are reference examples, not transcripts.

## What is EC2?

Amazon Elastic Compute Cloud (EC2) gives you virtual machines ("instances") that you rent by
the second. You pick the OS image, the hardware shape, the network and the disks; AWS owns
the physical host, the hypervisor (Nitro on current generations) and the data centre.

The way I think about it: an EC2 instance is just a Linux box like the Ubuntu container I
used in Session 2, except that its **network** lives in a VPC, its **disk** is usually a
network volume (EBS), and its **identity** comes from an IAM role rather than a user account.

- EC2 is **regional**; each instance lives in one **Availability Zone**, inside one subnet.
- On-Demand Linux instances are billed **per second** (with a 60-second minimum) while
  they are running. Stopped instances don't pay for compute, but their EBS volumes and any
  public IPv4 addresses are still billed.

## AMI (Amazon Machine Image)

An AMI is the template an instance boots from: one or more EBS snapshots for the root (and
optional data) volumes, a block device mapping, architecture (`x86_64` or `arm64`), and
launch permissions (who may use it).

Sources: AWS-provided (Amazon Linux 2023, plus vendor images such as Ubuntu and Windows),
AWS Marketplace, community AMIs, and your own (bake one with Packer or "Create image").

Gotchas:

- **AMI IDs are regional.** `ami-...` in `us-east-1` means nothing in `ap-south-1`; you copy
  the AMI between regions and it gets a new ID.
- **Don't hard-code AMI IDs.** Look up the latest one, e.g. via the public SSM parameter
  `/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64` or an `aws_ami`
  data source in Terraform.
- **Deregistering an AMI doesn't delete its snapshots.** They keep costing money until you
  delete them too.
- **Architecture must match the instance type.** An `arm64` AMI only boots on Graviton
  instances.

## Instance types

The name encodes the hardware. Take `m7g.xlarge`:

| Part | Value | Meaning |
|---|---|---|
| Family | `m` | General purpose |
| Generation | `7` | Higher is newer and usually better price/performance |
| Attributes | `g` | AWS Graviton (ARM). Others: `i` Intel, `a` AMD, `d` local NVMe instance store, `n` enhanced networking |
| Size | `xlarge` | vCPU / memory scale within the family |

| Family | Letters | Optimised for | Typical workload |
|---|---|---|---|
| General purpose | M, T | Balanced CPU / memory | Web/app servers, small databases |
| Compute optimised | C | High CPU per GiB RAM | Batch, encoding, CI builds |
| Memory optimised | R, X | High RAM per vCPU | Caches, in-memory analytics, big databases |
| Storage optimised | I, D | Fast local disks / high sequential throughput | NoSQL, data warehousing, log processing |
| Accelerated | P, G, Inf, Trn | GPUs / ML chips | ML training and inference, graphics |

**Burstable (T family)**: T instances earn CPU credits below a baseline and spend them when
they burst. T3, T3a and T4g launch in **unlimited mode by default**, meaning they can burst
past their credits, and sustained high CPU is billed extra. A "cheap" `t3.micro` pegged at
100% CPU all month is not as cheap as it looks.

## Key pairs

A key pair is an SSH key pair where AWS keeps **only the public key**. At first boot,
cloud-init writes it into `~/.ssh/authorized_keys` for the default user (`ec2-user` on
Amazon Linux, `ubuntu` on Ubuntu).

- If AWS creates the key, the private key is shown **once**. Lose it and you can't download
  it again.
- You can import your own public key instead (`aws ec2 import-key-pair`).
- Types: RSA and ED25519 (ED25519 isn't supported for Windows instances).
- `chmod 400 key.pem`, or `ssh` refuses to use it.

Honestly, for Linux the better default today is **no key pair and no port 22 at all**:
use **SSM Session Manager** (access controlled by IAM, sessions can be logged) or **EC2
Instance Connect** (pushes a short-lived key per session).

## Security Groups

A security group is a **stateful** virtual firewall attached to the instance's network
interface:

- **Allow rules only**; anything not allowed is denied.
- **Stateful**: if inbound 443 is allowed, the response goes back out automatically.
- A new security group has **no inbound rules** and **allows all outbound**.
- Sources can be CIDRs **or other security groups**. "Allow 5432 from the app-tier SG" is
  much better than hard-coding IPs.
- Rule changes apply immediately to running instances.

The SG vs NACL comparison lives in the [VPC notes](../04-vpc/README.md).

## EBS (Elastic Block Store)

EBS volumes are network-attached block devices: the instance's "hard disk", which lives
independently of the instance.

- A volume is **AZ-scoped**: it can only attach to an instance in the same AZ. To move it,
  snapshot it and create a new volume from the snapshot in the other AZ.
- **Snapshots** are incremental, stored by AWS in S3 behind the scenes, and are regional.
- **Delete on termination**: the root volume is deleted with the instance by default; data
  volumes attached after launch are preserved by default. Check the flag rather than assume.
- **Encryption**: per volume with KMS. You can turn on "encryption by default" per region.

| Type | Kind | Notes |
|---|---|---|
| `gp3` | SSD, general purpose | Baseline of 3,000 IOPS and 125 MiB/s regardless of size; more can be provisioned independently. The sensible default |
| `gp2` | SSD, general purpose (older) | IOPS scale with size (burst bucket for small volumes); migrate to gp3 |
| `io2` Block Express | SSD, provisioned IOPS | Highest IOPS and durability, for critical databases; supports Multi-Attach |
| `st1` | HDD, throughput optimised | Big sequential reads (logs, ETL). Can't be a boot volume |
| `sc1` | HDD, cold | Cheapest; infrequent access. Can't be a boot volume |

**Instance store** is different: physical NVMe disks on the host (the `d` in `m6id`). Very
fast, but **ephemeral**. Data survives a reboot and is **lost on stop, hibernate or
terminate**. Only for caches, scratch space and replicated data.

## Public vs private IP

| | Private IPv4 | Auto-assigned public IPv4 | Elastic IP |
|---|---|---|---|
| Where from | Subnet CIDR | Amazon's pool | Allocated to your account |
| Lifetime | Life of the instance | Released on **stop / hibernate / terminate**; new one on start | Yours until you release it |
| Survives stop/start? | Yes | **No** | Yes |
| Cost | Free | Charged per hour | Charged per hour, attached or not |

Things that surprised me:

- **The OS never sees the public IP.** `ip addr` inside the instance shows only the
  private address. The internet gateway does a 1:1 NAT between the two. To find the public
  IP from inside, ask the metadata service.
- **AWS charges for all public IPv4 addresses**, including ones attached to running
  instances, not just idle Elastic IPs. Another reason to keep instances in private subnets
  behind a load balancer.

```bash
# Inside the instance, IMDSv2 style (token first):
TOKEN=$(curl -sX PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 300")
curl -s -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/public-ipv4
```

## Instance lifecycle

```text
          launch
            |
            v
         pending ----> running ----(reboot: stays running)
                        |    ^
              stop /    |    |  start
              hibernate v    |
                     stopping --> stopped
                        |
          terminate     v
     (from running or stopped)
                  shutting-down --> terminated  (visible for a while, then gone)
```

What each action does to the things you care about:

| | Reboot | Stop | Hibernate | Terminate |
|---|---|---|---|---|
| Compute billing | Continues | Stops (EBS still billed) | Stops once stopped (billed while saving RAM) | Stops |
| Physical host | Same | Usually moves | Usually moves | Gone |
| Private IPv4 | Kept | Kept | Kept | Released |
| Auto-assigned public IPv4 | Kept | **Released** | **Released** | Released |
| Elastic IP | Kept | Stays associated | Stays associated | Disassociated, **still allocated and billed** |
| RAM contents | Lost (OS reboot) | Lost | **Saved to the encrypted EBS root and restored** | Lost |
| Instance store data | Kept | **Lost** | **Lost** | Lost |
| EBS root volume | Kept | Kept | Kept | Deleted if `DeleteOnTermination` is true (default for root) |

Hibernation has to be **enabled at launch**, needs an **encrypted EBS root volume** large
enough to hold RAM, and only works on supported instance types and sizes.

Two safety switches: **termination protection** (`disable_api_termination`) and the
**shutdown behaviour** setting (does `shutdown -h now` inside the OS stop or terminate?).

## Common use cases

- **Web and API servers** in an Auto Scaling group behind an Application Load Balancer.
- **Kubernetes worker nodes** (EKS managed node groups are EC2 underneath).
- **CI runners and batch jobs**, often on **Spot** (spare capacity at a large discount, but
  AWS can reclaim it with a two-minute warning).
- **Self-managed software** that has no managed equivalent or needs OS-level control.
- **Bastion hosts**, although Session Manager mostly makes these unnecessary.

Pricing options to know: On-Demand (no commitment), Savings Plans / Reserved Instances
(commit to 1 or 3 years for a discount), Spot (interruptible), Dedicated Hosts (licensing
or compliance).

## Terraform example (for reference)

A small web server: latest Amazon Linux 2023 AMI, IMDSv2 enforced, encrypted gp3 root,
HTTP open, no SSH (manage it via SSM using the role from the IAM notes).

```hcl
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
}

resource "aws_security_group" "web" {
  name        = "session18-web"
  description = "HTTP in, everything out"
  vpc_id      = var.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "http" {
  security_group_id = aws_security_group.web.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
}

# Terraform removes AWS's default allow-all egress rule, so add it back explicitly
resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.web.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_instance" "web" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = "t3.micro"
  subnet_id              = var.public_subnet_id
  vpc_security_group_ids = [aws_security_group.web.id]
  iam_instance_profile   = aws_iam_instance_profile.app.name

  metadata_options {
    http_tokens = "required" # IMDSv2 only
  }

  root_block_device {
    volume_type = "gp3"
    volume_size = 10
    encrypted   = true
  }

  user_data = <<-EOF
    #!/bin/bash
    dnf install -y nginx
    systemctl enable --now nginx
  EOF

  tags = {
    Name = "session18-web"
  }
}
```

`user_data` runs **once**, as root, on the **first boot** only (via cloud-init). Editing it
later doesn't re-run it on the existing instance.

## Commands worth knowing

Reference only; not run on this machine. `i-0123456789abcdef0` is a placeholder.

```bash
# Running instances with their IPs
aws ec2 describe-instances \
  --filters Name=instance-state-name,Values=running \
  --query 'Reservations[].Instances[].[InstanceId,InstanceType,PrivateIpAddress,PublicIpAddress]' \
  --output table

# Latest Amazon Linux 2023 AMI ID for the current region
aws ssm get-parameter \
  --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 \
  --query Parameter.Value --output text

# Compare instance types before choosing
aws ec2 describe-instance-types --instance-types t3.micro t4g.micro \
  --query 'InstanceTypes[].[InstanceType,VCpuInfo.DefaultVCpus,MemoryInfo.SizeInMiB]' \
  --output table

# Create an ED25519 key pair and save the private key once
aws ec2 create-key-pair --key-name session18 --key-type ed25519 \
  --query KeyMaterial --output text > session18.pem
chmod 400 session18.pem

# Lifecycle
aws ec2 stop-instances --instance-ids i-0123456789abcdef0
aws ec2 stop-instances --instance-ids i-0123456789abcdef0 --hibernate
aws ec2 start-instances --instance-ids i-0123456789abcdef0
aws ec2 terminate-instances --instance-ids i-0123456789abcdef0

# Shell without SSH (needs the Session Manager plugin and the SSM role)
aws ssm start-session --target i-0123456789abcdef0
```

## Key takeaways

- An instance = AMI (what it boots) + instance type (hardware shape) + subnet and security
  groups (network) + EBS (disk) + IAM role (identity).
- Stopping releases the auto-assigned public IP and wipes instance store; hibernate keeps
  RAM; terminate deletes the root volume by default.
- EBS is AZ-scoped and persistent; instance store is fast and ephemeral.
- Public IPv4 addresses cost money and the OS never sees them. Prefer private subnets
  behind a load balancer.
- Skip SSH keys and port 22 where possible: SSM Session Manager plus IMDSv2 is the safer
  default.

## References

- What is Amazon EC2? — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/concepts.html
- Amazon Machine Images — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AMIs.html
- Instance types — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-types.html
- Burstable performance instances — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-performance-instances.html
- Key pairs — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html
- Security groups for EC2 — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-security-groups.html
- Instance IP addressing — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-instance-addressing.html
- Instance state changes (lifecycle) — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-lifecycle.html
- Hibernate your instance — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Hibernate.html
- Instance store — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/InstanceStorage.html
- What is Amazon EBS? — https://docs.aws.amazon.com/ebs/latest/userguide/what-is-ebs.html
- EBS volume types — https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volume-types.html
