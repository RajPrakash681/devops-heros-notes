# Session 18 — AWS Services — 05: DynamoDB & RDS (Database)

- **Name:** Raj Prakash
- **Enrollment No:** 24BCS10328

---

> Research notes for Session 18, Task 2. No AWS credentials on this machine, so nothing
> below was run. CLI and Terraform blocks are reference examples, not transcripts.

Two very different answers to "where does my data live?". DynamoDB is a serverless
key-value store you design *around your queries*. RDS is a managed copy of a database
engine you already know, designed *around your data*.

# Part 1: DynamoDB

## NoSQL

Amazon DynamoDB is a fully managed, serverless **NoSQL key-value and document database**.
There are no servers, versions or patches to manage, and a well-designed table gives
consistent single-digit-millisecond latency at almost any scale.

"NoSQL" here means:

- **No joins and no ad-hoc queries.** You fetch items by key (or by key range). Everything
  else is either a secondary index you planned for, or an expensive full-table `Scan`.
- **No fixed schema** apart from the key attributes.
- **Design starts from access patterns.** With SQL I'd model the entities and query them
  any way later. With DynamoDB I list the queries first ("get user profile", "list a user's
  orders newest first") and shape the keys to answer exactly those. That reversal was the
  biggest mindset shift for me.

Data is automatically replicated across multiple AZs in the region. Reads are **eventually
consistent by default**; strongly consistent reads are available on the table (not on
global secondary indexes) and cost twice as much.

## Tables

A table is a collection of items. You define its **primary key** and its **capacity mode**
when you create it:

| Capacity mode | How you pay | When |
|---|---|---|
| **On-demand** | Per request | Unknown, spiky or new workloads; the usual default today |
| **Provisioned** | Per hour for read/write capacity units (RCU/WCU), optionally auto-scaled | Steady, predictable traffic where it's cheaper |

Capacity units: **1 RCU** = one strongly consistent read per second (or two eventually
consistent reads) of an item up to 4 KB. **1 WCU** = one write per second of an item up to
1 KB. A 9 KB item therefore costs 3 RCU per strongly consistent read.

Useful table features: **TTL** (free automatic deletes of expired items, typically within a
few days, not to the second), **Streams** (change feed for Lambda), **point-in-time
recovery**, **global tables** (multi-region), and **deletion protection**.

## Items

An item is one record, roughly a row, identified by its primary key. Items in the same
table can have completely different attributes.

- **Maximum item size is 400 KB**, attribute names included. Large blobs go to S3, with the
  S3 key stored in the item.

## Attributes

Attributes are name/value pairs. Types: scalars (**String, Number, Binary, Boolean,
Null**), documents (**List, Map**) and sets (**String Set, Number Set, Binary Set**).

The low-level API (and so the CLI) uses typed JSON:

```json
{
  "pk":     { "S": "USER#42" },
  "sk":     { "S": "ORDER#2026-10-05#9002" },
  "total":  { "N": "1499" },
  "status": { "S": "PLACED" }
}
```

Numbers are sent as strings (`"N": "1499"`) so no precision is lost in transit.

## Partition key

The partition key (also called the hash key) decides **where an item physically lives**.
DynamoDB hashes it to pick a partition. A table can use a partition key alone (simple
primary key) or partition key + sort key (composite).

**Hot partitions** are the classic DynamoDB failure. Each partition is designed for a
maximum of **3,000 read units and 1,000 write units per second**. Adaptive capacity and
automatic partition splitting smooth out a lot of skew, but they can't do much when
traffic concentrates on a single item or a handful of keys. Then you get throttled
(`ProvisionedThroughputExceededException` or `ThrottlingException`) even though the table
as a whole "has capacity".

| Partition key choice | Outcome |
|---|---|
| `status` (`PLACED` / `SHIPPED`) | Terrible: two values, everything piles onto two keys |
| `date` for an events table | Bad: every write today hits one key |
| `user_id`, `order_id`, `device_id` | Good: high cardinality, traffic spreads out |
| `date#<random 0-9>` (write sharding) | Fixes the date case; reads query all 10 shards and merge |

## Sort key

The sort key (range key) orders items **within** one partition key value. Items sharing a
partition key form an *item collection*, and the sort key unlocks range queries on it:
`=`, `<`, `>`, `BETWEEN`, `begins_with`.

A small single-table design for users and orders:

| `pk` | `sk` | Other attributes |
|---|---|---|
| `USER#42` | `PROFILE` | name, email |
| `USER#42` | `ORDER#2026-10-01#9001` | total, status |
| `USER#42` | `ORDER#2026-10-05#9002` | total, status |

`pk = USER#42 AND begins_with(sk, "ORDER#")` returns that user's orders already sorted by
date, in one request. Other access patterns (say, "all orders with status `PLACED`") need a
**global secondary index** with its own key. Local secondary indexes keep the same
partition key and must be created together with the table.

Two more gotchas:

- **`Scan` reads the whole table**, and **filter expressions run after the read**, so you
  pay capacity for everything read, not what's returned.
- Many common words (`status`, `name`, `date`, ...) are **reserved words** in expressions;
  use placeholders like `#s` with `ExpressionAttributeNames`.

## Use cases

- User profiles, sessions and shopping carts (fetch-by-key at high scale).
- Serverless backends (Lambda + API Gateway + DynamoDB).
- IoT and event data with TTL to expire old records.
- Leaderboards, counters, feature flags, idempotency keys.
- Historically, **Terraform state locking** (`dynamodb_table` in the S3 backend). That
  option is now deprecated in favour of `use_lockfile = true`, which locks with a file in
  the state bucket itself.

# Part 2: RDS

## Relational database

Amazon RDS runs a relational database engine for you: provisioning, OS and engine patching,
automated backups, failure detection and failover, and monitoring. You keep SQL, joins,
transactions, constraints and your existing tools. You give up OS/SSH access (outside RDS
Custom) and some superuser privileges.

What stays my job: schema and query design, indexes, choosing the instance size, parameter
tuning, and planning major-version upgrades.

## Supported engines

RDS supports **PostgreSQL, MySQL, MariaDB, Oracle Database, Microsoft SQL Server and IBM
Db2**. **Amazon Aurora** (MySQL- and PostgreSQL-compatible) is managed through the RDS
console and API but is a separate AWS-built engine with its own shared storage layer and
its own user guide.

## DB instances

A DB instance is the unit you create: an isolated database environment with a **DNS
endpoint**, an **instance class** and **storage**.

- **Instance classes** follow EC2 naming with a `db.` prefix: burstable `db.t4g`, general
  purpose `db.m*`, memory optimised `db.r*`.
- **Storage**: gp3 / gp2 / io1 / io2 EBS-backed. Storage can be **increased but not
  shrunk**; storage autoscaling grows it up to a ceiling you set.
- **Always connect to the endpoint hostname, never an IP.** Failover works by repointing
  the DNS name, and the IP changes.
- **Parameter groups** hold engine settings (some changes need a reboot); a **DB subnet
  group** lists the subnets, in at least two AZs, that RDS may use.

## Security

Layered, like everything else in AWS:

| Layer | What to do |
|---|---|
| Network | Private/isolated subnets, `publicly_accessible = false`, security group allowing the DB port only from the app tier's SG (see the [VPC notes](../04-vpc/README.md)) |
| Encryption at rest | KMS encryption **chosen at creation**. An existing unencrypted instance can't be encrypted in place: snapshot, copy the snapshot with encryption, restore |
| Encryption in transit | TLS between client and DB; can be enforced through parameter groups |
| Credentials | Let RDS manage the master password in **Secrets Manager** (with rotation), or use **IAM database authentication** (short-lived tokens) |
| Control plane | IAM policies decide who can modify, snapshot or delete instances |

## Backups

- **Automated backups**: a daily snapshot plus transaction logs, with a retention period of
  **0 to 35 days** (0 turns them off). Together they allow **point-in-time restore** to any
  second in the window, up to a few minutes ago.
- **Manual snapshots**: kept until you delete them, even after the instance is gone. Take
  one before every risky migration.
- **A restore always creates a *new* DB instance** with a new endpoint. It doesn't
  overwrite the old one, so the application has to be pointed at the new endpoint.
- Deleting an instance prompts for a **final snapshot**. In Terraform that's
  `skip_final_snapshot` / `final_snapshot_identifier`, and getting it wrong either loses
  data or blocks `terraform destroy`.

## Multi-AZ

Multi-AZ is about **high availability and durability, not performance**.

- **Multi-AZ DB instance (the classic form)**: RDS keeps a **synchronous standby** in another
  AZ. On a failure of the primary (or its AZ, or during some maintenance) RDS fails over
  automatically by repointing the endpoint DNS name, **typically in 60–120 seconds**. The
  standby **can't serve reads**; it's a hot spare.
- **Multi-AZ DB cluster** (MySQL and PostgreSQL): one writer plus **two readable standbys**
  across three AZs with semisynchronous replication, and generally faster failover.

Because writes commit to two AZs, latency is slightly higher. That's the price of not
losing committed data when an AZ goes down.

## Read replicas

Read replicas are about **scaling reads**.

- **Asynchronous** replication from the source, so replicas can **lag**: a user may not see
  their own write if the read goes to a replica.
- Each replica has **its own endpoint**; the application (or a proxy) must send reads there.
- **Up to 15 read replicas** per source instance, in the same region or **cross-region**
  (useful for DR and for serving users closer to them).
- A replica can be **promoted** to a standalone, writable instance. Promotion is manual and
  one-way, and breaks replication.
- Automated backups must be enabled on the source.

| | Multi-AZ instance | Multi-AZ DB cluster | Read replica |
|---|---|---|---|
| Goal | High availability | HA + some read capacity | Read scaling, cross-region DR |
| Replication | Synchronous | Semisynchronous | Asynchronous |
| Standby readable? | No | Yes (2 readers) | Yes |
| Failover | Automatic, same endpoint | Automatic, same endpoint | Manual promotion, new endpoint |
| Region | Same region, another AZ | Same region, three AZs | Same or another region |

They combine: a production database is often Multi-AZ *and* has read replicas.

## Use cases

- Classic web and business applications: orders, payments, inventory, anything needing
  multi-row **ACID transactions** and referential integrity.
- Reporting and ad-hoc SQL over relational data (often against a read replica).
- Lift-and-shift of existing MySQL / PostgreSQL / SQL Server / Oracle databases, and
  off-the-shelf software that expects SQL (Keycloak, a CMS, Grafana in HA mode).

# DynamoDB vs RDS

| | DynamoDB | RDS |
|---|---|---|
| Model | Key-value / document (NoSQL) | Relational tables (SQL) |
| Schema | Only the key attributes are fixed | Fixed schema, migrations |
| Queries | By key and key range; indexes planned up front | Arbitrary SQL, joins, aggregations |
| Scaling | Horizontal and automatic via partitions | Vertical (bigger instance) + read replicas |
| Servers | None (serverless) | DB instances you size and pay for hourly |
| Pricing | Per request (on-demand) or per capacity unit + storage | Per instance-hour + storage (+ provisioned IOPS, extra backup storage) |
| HA | Multi-AZ built in; global tables for multi-region | Opt-in Multi-AZ; cross-region read replicas |
| Limits to know | 400 KB item, per-partition throughput | Instance size, connection count, storage can't shrink |
| Pick it when | Access patterns are known and scale or latency matters | Data is relational, queries vary, transactions span tables |

## Terraform examples (for reference)

DynamoDB table for the single-table design above. Only **key attributes** go in
`attribute` blocks; declaring a non-key attribute is an error.

```hcl
resource "aws_dynamodb_table" "orders" {
  name         = "session18-orders"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  deletion_protection_enabled = true
}
```

PostgreSQL on RDS, private, encrypted, Multi-AZ, with a read replica. The subnets and the
`db` security group come from the VPC setup.

```hcl
resource "aws_db_subnet_group" "main" {
  name       = "session18-db"
  subnet_ids = [aws_subnet.db_a.id, aws_subnet.db_b.id]
}

resource "aws_db_instance" "main" {
  identifier     = "session18-postgres"
  engine         = "postgres"
  engine_version = "16"
  instance_class = "db.t4g.micro"

  allocated_storage     = 20
  max_allocated_storage = 100 # storage autoscaling ceiling
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name                     = "appdb"
  username                    = "appadmin"
  manage_master_user_password = true # password lives in Secrets Manager, not in state

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false
  multi_az               = true

  backup_retention_period   = 7
  deletion_protection       = true
  skip_final_snapshot       = false
  final_snapshot_identifier = "session18-postgres-final"
}

resource "aws_db_instance" "replica" {
  identifier             = "session18-postgres-ro"
  replicate_source_db    = aws_db_instance.main.identifier
  instance_class         = "db.t4g.micro"
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false
  skip_final_snapshot    = true
}
```

## Commands worth knowing

Reference only; not run on this machine.

```bash
# DynamoDB
aws dynamodb put-item --table-name session18-orders \
  --item '{"pk":{"S":"USER#42"},"sk":{"S":"ORDER#2026-10-05#9002"},"total":{"N":"1499"}}'

aws dynamodb query --table-name session18-orders \
  --key-condition-expression 'pk = :pk AND begins_with(sk, :o)' \
  --expression-attribute-values '{":pk":{"S":"USER#42"},":o":{"S":"ORDER#"}}'

# RDS
aws rds describe-db-instances \
  --query 'DBInstances[].[DBInstanceIdentifier,Engine,DBInstanceStatus,MultiAZ,Endpoint.Address]' \
  --output table

aws rds create-db-snapshot --db-instance-identifier session18-postgres \
  --db-snapshot-identifier session18-before-migration

# Test Multi-AZ failover on purpose (reboot with failover)
aws rds reboot-db-instance --db-instance-identifier session18-postgres --force-failover

# Point-in-time restore: creates a NEW instance
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier session18-postgres \
  --target-db-instance-identifier session18-postgres-restored \
  --restore-time 2026-10-07T09:30:00Z
```

## Key takeaways

- DynamoDB: design keys from access patterns. A high-cardinality partition key avoids hot
  partitions; the sort key gives range queries and ordering inside a partition.
- DynamoDB items max out at 400 KB, reads are eventually consistent by default, and `Scan`
  plus filters is a cost trap.
- RDS: a managed SQL engine (PostgreSQL, MySQL, MariaDB, Oracle, SQL Server, Db2). Connect
  by endpoint, keep it private, and choose encryption at creation.
- Multi-AZ = synchronous standby for HA (not readable in the classic form). Read replicas =
  asynchronous copies for read scaling, which can lag.
- Restores and point-in-time recovery create a new instance with a new endpoint. Plan the
  cut-over before you need it.

## References

- What is Amazon DynamoDB? — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html
- DynamoDB core components — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.CoreComponents.html
- Partition key design best practices — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html
- DynamoDB throughput capacity — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/capacity-mode.html
- DynamoDB quotas — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/ServiceQuotas.html
- What is Amazon RDS? — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html
- RDS DB instances — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Overview.DBInstance.html
- Security in Amazon RDS — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.html
- RDS backups — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.html
- RDS Multi-AZ deployments — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.html
- RDS read replicas — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReadRepl.html
