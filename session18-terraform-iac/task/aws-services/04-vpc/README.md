# Session 18 — AWS Services — 04: VPC (Networking)

- **Name:** Raj Prakash
- **Enrollment No:** 2024EB02289

---

> Research notes for Session 18, Task 2. No AWS credentials on this machine, so nothing
> below was run. CLI and Terraform blocks are reference examples, not transcripts.

## What is VPC?

A Virtual Private Cloud is your own logically isolated network inside an AWS region. You
choose the IP range, carve it into subnets, decide which subnets can reach the internet,
and put firewalls in front of everything. EC2 instances, RDS databases, load balancers and
EKS nodes all live inside a VPC.

What made VPCs click for me was mapping them onto the Session 4 networking basics:

| On-prem idea | VPC equivalent |
|---|---|
| Private address space (RFC 1918) | VPC CIDR, e.g. `10.0.0.0/16` |
| VLAN / network segment | Subnet |
| Router + routing table | Implicit VPC router + route tables |
| Edge router to the ISP | Internet Gateway |
| Home router doing NAT | NAT Gateway |
| Host firewall | Security group |
| Stateless ACL on a router port | Network ACL |

- A VPC is **regional** and spans every AZ in the region. **Subnets are per-AZ.**
- Every region has a **default VPC** (`172.31.0.0/16`, a public subnet in each AZ, an IGW
  attached). It's handy for experiments, but real workloads should get their own VPC with a
  deliberate layout.

## CIDR

The VPC's primary IPv4 block is chosen at creation and **can't be changed** afterwards (you
can add secondary CIDR blocks). Allowed sizes are **`/16` (65,536 addresses) down to `/28`
(16 addresses)**.

| Prefix | Addresses | Usable in a subnet (minus 5 reserved) |
|---|---|---|
| `/16` | 65,536 | (VPC size) |
| `/20` | 4,096 | 4,091 |
| `/24` | 256 | 251 |
| `/28` | 16 | 11 |

**AWS reserves 5 addresses in every subnet.** For `10.0.0.0/24`:

| Address | Reserved for |
|---|---|
| `10.0.0.0` | Network address |
| `10.0.0.1` | VPC router |
| `10.0.0.2` | DNS (the Amazon DNS server is at the VPC base + 2) |
| `10.0.0.3` | Reserved for future use |
| `10.0.0.255` | Broadcast (not supported in a VPC, but reserved anyway) |

Planning advice I'm taking to heart: **don't overlap CIDRs** with other VPCs, on-prem
networks or partner networks you might ever peer with or VPN into. Overlaps can't be fixed
later without rebuilding. And don't make the VPC so small that EKS (one IP per pod) runs
out of addresses.

## Subnets

A subnet is a slice of the VPC CIDR that lives in exactly **one AZ**. High availability
therefore means **at least one subnet per tier per AZ**.

A typical two-AZ, three-tier layout in `ap-south-1`:

```text
VPC 10.0.0.0/16
|
|-- ap-south-1a
|   |-- public-a   10.0.0.0/24    route: 0.0.0.0/0 -> igw        (ALB, NAT gateway)
|   |-- app-a      10.0.10.0/24   route: 0.0.0.0/0 -> nat-a      (EC2 / EKS nodes)
|   |-- db-a       10.0.20.0/24   route: local only              (RDS)
|
|-- ap-south-1b
    |-- public-b   10.0.1.0/24    route: 0.0.0.0/0 -> igw
    |-- app-b      10.0.11.0/24   route: 0.0.0.0/0 -> nat-b
    |-- db-b       10.0.21.0/24   route: local only
```

## Route tables

Every subnet is associated with exactly one route table. A route table can serve many
subnets. Subnets without an explicit association use the VPC's **main route table**.

- Each route table has a **`local` route** for the VPC CIDR. That's why everything in a VPC
  can reach everything else by default (security groups and NACLs permitting).
- The most specific route wins (**longest prefix match**): `10.0.0.0/16 -> local` beats
  `0.0.0.0/0 -> igw` for internal traffic.

Public subnet route table:

| Destination | Target |
|---|---|
| `10.0.0.0/16` | `local` |
| `0.0.0.0/0` | `igw-...` |

Private (app) subnet route table:

| Destination | Target |
|---|---|
| `10.0.0.0/16` | `local` |
| `0.0.0.0/0` | `nat-...` |
| `pl-...` (S3 prefix list) | `vpce-...` (S3 gateway endpoint) |

Gotcha: **don't add `0.0.0.0/0 -> igw` to the main route table.** Every new subnet that
nobody explicitly associates would silently become public. Keep the main table private and
associate public subnets explicitly.

## Internet Gateway

An Internet Gateway (IGW) connects a VPC to the internet.

- **One IGW per VPC**, horizontally scaled and highly available. There is nothing to size
  or patch.
- **No hourly charge for the IGW itself.** You pay for data transfer out to the internet and
  for public IPv4 addresses, not for the gateway.
- For an instance to be reachable from the internet it needs all of: a **public IPv4 or
  Elastic IP**, a subnet route `0.0.0.0/0 -> igw`, and **security group and NACL rules**
  allowing the traffic. Missing any one of the three is the usual "why can't I connect"
  answer.
- The IGW performs the 1:1 NAT between an instance's private IP and its public IP, which is
  why the OS only ever sees its private address.
- For IPv6, outbound-only access uses an **egress-only internet gateway** instead of NAT.

## NAT Gateway

A NAT Gateway lets resources in private subnets **start** outbound IPv4 connections (OS
updates, pulling container images, calling external APIs) while **nothing on the internet
can start a connection to them**.

The classic (**zonal**) NAT gateway:

- Lives in a **public subnet** in one AZ and uses an **Elastic IP**.
- Private subnets route `0.0.0.0/0` to it.
- **Is zonal**: if its AZ fails, subnets routing to it lose internet. For HA, run one per
  AZ and point each private route table at the NAT **in its own AZ** (which also avoids
  cross-AZ data charges).

AWS has since added **regional NAT gateways**, which spread across AZs automatically and
don't need a public subnet. Zonal mode is still required for private NAT
(private-to-private translation).

**Cost: NAT gateways are not free.** You pay an **hourly charge per NAT gateway** *and* a
**per-GB data processing charge** on everything that flows through it, on top of normal data
transfer. Three AZs means three NAT gateways billed around the clock, even in an idle dev
account. Common savings:

- **Gateway VPC endpoints for S3 and DynamoDB are free.** Without them, a private instance
  pulling gigabytes from S3 pays NAT processing on every byte.
- Interface endpoints (PrivateLink) for other AWS services (ECR, CloudWatch, SSM), which have
  their own hourly + per-GB price but can beat NAT on heavy traffic.
- In dev, a single NAT gateway (accepting the AZ risk), or none at all if nothing needs the
  internet.

## Security Groups

Covered from the instance side in the [EC2 notes](../02-ec2/README.md). The network-level
points:

- **Stateful**: return traffic is automatically allowed, so you only write rules for the
  side that *initiates* the connection.
- **Allow-only**; all rules are evaluated together, so order doesn't matter.
- Attached to **network interfaces** (instances, RDS, Lambda in a VPC, load balancers),
  up to five per interface by default.
- Can reference **other security groups** as sources. This is the idiomatic tier model:

| SG | Inbound rule |
|---|---|
| `alb-sg` | TCP 443 from `0.0.0.0/0` |
| `app-sg` | TCP 8080 from `alb-sg` |
| `db-sg` | TCP 5432 from `app-sg` |

No IP addresses anywhere, and it keeps working as instances scale in and out.

## Network ACLs

A network ACL is a **stateless** firewall at the **subnet boundary**.

- **Stateless**: return traffic is *not* automatic. If you allow inbound 443, you must also
  allow the outbound response to the client's **ephemeral port**. AWS suggests allowing
  `1024-65535` because clients (and NAT gateways) use different ranges.
- **Numbered rules, evaluated lowest number first, first match wins.** The last rule (`*`)
  denies anything unmatched.
- Supports **Allow and Deny**. This is the main reason to touch NACLs at all: blocking a
  specific CIDR, which security groups can't do.
- The **default NACL allows everything** in both directions. A **new custom NACL denies
  everything** until you add rules.
- Each subnet has exactly one NACL; one NACL can cover many subnets.

Example inbound rules for a public web subnet that blocks one abusive address:

| Rule # | Protocol | Port | Source | Action |
|---|---|---|---|---|
| 90 | All | All | `203.0.113.50/32` | **DENY** |
| 100 | TCP | 443 | `0.0.0.0/0` | ALLOW |
| 110 | TCP | 1024-65535 | `0.0.0.0/0` | ALLOW (responses to outbound connections) |
| `*` | All | All | `0.0.0.0/0` | DENY |

Rule 90 has to be numbered *below* 100, otherwise the 443 allow would match first.

### Security group vs NACL

| | Security group | Network ACL |
|---|---|---|
| Level | Network interface (instance) | Subnet |
| State | **Stateful** | **Stateless** |
| Rules | Allow only | Allow and Deny |
| Evaluation | All rules together | Numbered order, first match wins |
| Default | New SG: no inbound, all outbound | Default NACL: allow all; new custom NACL: deny all |
| Typical use | Primary, fine-grained access control | Coarse subnet guardrails, blocking CIDRs |

## Public vs private subnet

The difference is **only the route table**: AWS has no "public" checkbox.

| | Public subnet | Private subnet | Isolated subnet |
|---|---|---|---|
| Default route | `0.0.0.0/0 -> igw` | `0.0.0.0/0 -> nat` | None (local only) |
| Inbound from internet | Possible (with public IP + SG) | No | No |
| Outbound to internet | Directly via IGW | Via NAT gateway | No |
| Auto-assign public IP | Usually on | Off | Off |
| Put here | ALB, NAT gateway, (bastion) | App servers, EKS nodes | Databases |

A packet from a private app server to `api.github.com` goes: instance -> security group
(outbound) -> subnet NACL (outbound) -> private route table (`0.0.0.0/0 -> nat`) -> NAT
gateway in the public subnet -> public route table (`0.0.0.0/0 -> igw`) -> IGW -> internet.
The response comes back the same way, and the NACLs have to allow it explicitly.

## Terraform example (for reference)

One AZ's worth of the layout above: VPC, IGW, public and private subnets, NAT gateway, and a
free S3 gateway endpoint.

```hcl
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true # off by default for non-default VPCs

  tags = { Name = "session18-vpc" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
}

resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.0.0/24"
  availability_zone       = "ap-south-1a"
  map_public_ip_on_launch = true
}

resource "aws_subnet" "app_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.10.0/24"
  availability_zone = "ap-south-1a"
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
}

resource "aws_route_table_association" "public_a" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public.id
}

resource "aws_eip" "nat_a" {
  domain = "vpc"
}

resource "aws_nat_gateway" "a" {
  allocation_id = aws_eip.nat_a.id
  subnet_id     = aws_subnet.public_a.id
  depends_on    = [aws_internet_gateway.main]
}

resource "aws_route_table" "private_a" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.a.id
  }
}

resource "aws_route_table_association" "app_a" {
  subnet_id      = aws_subnet.app_a.id
  route_table_id = aws_route_table.private_a.id
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.ap-south-1.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private_a.id]
}
```

In a real project I'd reach for the community `terraform-aws-modules/vpc/aws` module rather
than hand-writing every route, but writing it out once is how the pieces made sense.

## Commands worth knowing

Reference only; not run on this machine. `vpc-0123456789abcdef0` is a placeholder.

```bash
aws ec2 describe-vpcs \
  --query 'Vpcs[].[VpcId,CidrBlock,IsDefault]' --output table

aws ec2 describe-subnets --filters Name=vpc-id,Values=vpc-0123456789abcdef0 \
  --query 'Subnets[].[SubnetId,AvailabilityZone,CidrBlock,MapPublicIpOnLaunch,AvailableIpAddressCount]' \
  --output table

aws ec2 describe-route-tables --filters Name=vpc-id,Values=vpc-0123456789abcdef0 \
  --query 'RouteTables[].[RouteTableId,Routes[].[DestinationCidrBlock,GatewayId,NatGatewayId]]'

aws ec2 describe-nat-gateways \
  --query 'NatGateways[].[NatGatewayId,State,SubnetId]' --output table

aws ec2 describe-network-acls --filters Name=vpc-id,Values=vpc-0123456789abcdef0
```

For debugging real traffic, **VPC Flow Logs** (accepted/rejected flows per interface, subnet
or VPC) and **Reachability Analyzer** (does a path exist from A to B, and which hop blocks
it?) are the tools to reach for.

## Key takeaways

- A VPC is regional; subnets are per-AZ. HA means a subnet per tier in each AZ.
- "Public subnet" just means its route table sends `0.0.0.0/0` to an internet gateway.
  Keep the main route table private.
- AWS reserves 5 IPs per subnet, and CIDRs can't be changed or un-overlapped later. Plan
  them up front.
- The IGW is free; NAT gateways cost per hour and per GB. Use free gateway endpoints for S3
  and DynamoDB.
- Security groups are stateful and allow-only; NACLs are stateless, numbered, first match
  wins, and need ephemeral-port rules for return traffic.

## References

- What is Amazon VPC? — https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html
- VPC CIDR blocks — https://docs.aws.amazon.com/vpc/latest/userguide/vpc-cidr-blocks.html
- Subnets for your VPC — https://docs.aws.amazon.com/vpc/latest/userguide/configure-subnets.html
- Subnet CIDR blocks (reserved addresses) — https://docs.aws.amazon.com/vpc/latest/userguide/subnet-sizing.html
- Route tables — https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html
- Internet gateways — https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html
- NAT gateways — https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html
- Security groups — https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html
- Network ACLs — https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html
- Gateway endpoints — https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-endpoints.html
- VPC Flow Logs — https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html
