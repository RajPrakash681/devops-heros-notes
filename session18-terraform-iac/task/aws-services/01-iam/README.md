# Session 18 — AWS Services — 01: IAM (Governance)

- **Name:** Raj Prakash
- **Enrollment No:** 2024EB02289

---

> Research notes for Session 18, Task 2. I don't have AWS credentials on this machine, so
> none of the CLI or Terraform below was run. The snippets are reference examples I checked
> against the AWS docs and the Terraform AWS provider docs; there is no real output here.

## What is IAM?

AWS Identity and Access Management (IAM) answers two questions for every single API call
made to AWS:

1. **Authentication**: who is calling? (a user, a role session, a service)
2. **Authorization**: is that caller allowed to do *this action* on *this resource*,
   right now, under these conditions?

Every console click, CLI command and Terraform `apply` is just a signed API call, and IAM
evaluates it. That's the mental model that made IAM click for me: **IAM isn't a feature you
turn on; it's the gate in front of every AWS API.**

A few facts worth remembering:

- IAM is **global**, not regional. A role created "in" `ap-south-1` exists everywhere.
- IAM itself has **no charge**.
- IAM is **eventually consistent**. A policy change can take a short while to propagate, so
  automation that creates a role and uses it in the next second can fail intermittently.
- The **root user** (the email you signed up with) has full, unrestrictable access inside
  its account. Lock it down with MFA, create no access keys for it, and use it only for the
  handful of tasks that actually require root.

## Users

An IAM user is a long-lived identity inside one account. It can have:

- a **console password**, and/or
- up to **two access keys** (access key ID + secret). Two is deliberate: it lets you rotate
  by creating the new key, switching over, then deleting the old one.

The catch is that these credentials are **long-term**. They don't expire on their own, which
is exactly why leaked access keys in a public Git repo get abused within minutes. AWS's
current guidance is that humans should sign in through federation / IAM Identity Center
and get temporary credentials, and IAM users with access keys should be the exception
(e.g. a third-party tool that can't assume roles).

## Groups

A group is just a bag of users that share policies. Attach `ReadOnlyAccess` to a
`developers` group and every user in it gets read-only access.

Things that surprised me:

- Groups **can't be nested** (no group inside a group).
- A group is **not a principal**. You can't put a group ARN in the `Principal` of a bucket
  policy or a trust policy; only users, roles, accounts, services and federated identities
  can be principals.
- Groups only hold users, never roles.

## Roles

A role is an identity with permissions but **no long-term credentials**. Someone (or
something) *assumes* it through AWS STS and gets temporary credentials that expire.

Every role has two policies that do different jobs:

| Policy on the role | Question it answers | Example |
|---|---|---|
| **Trust policy** (resource-based) | *Who* is allowed to assume this role? | `ec2.amazonaws.com`, another account, GitHub's OIDC provider |
| **Permissions policy** (identity-based) | *What* can the role do once assumed? | `s3:GetObject` on one bucket |

Typical consumers of roles:

- **AWS services**: an EC2 instance (through an *instance profile*), a Lambda function, an
  ECS task.
- **Cross-account access**: a CI account deploying into a prod account.
- **Federation**: SSO users, or a CI system using OIDC instead of stored keys.

Example trust policy that lets GitHub Actions (only the `main` branch of one repo) assume
a deploy role via OIDC, with no AWS keys stored in GitHub at all:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:my-org/my-repo:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

The `sub` condition is the important part. Without it, *any* GitHub repository could ask
for this role.

## Policies

A policy is a JSON document. The core elements of each statement:

| Element | Meaning |
|---|---|
| `Effect` | `Allow` or `Deny` |
| `Action` | API actions, e.g. `s3:GetObject`, `ec2:StartInstances` (wildcards allowed) |
| `Resource` | ARNs the statement applies to |
| `Condition` | Optional extra checks: source IP, MFA present, tags, VPC endpoint, ... |
| `Principal` | Only in **resource-based** policies: who the statement applies to |
| `Sid` | Optional label, handy for reading and debugging |

`"Version": "2012-10-17"` is the policy language version, not a date you should update.

The main policy types:

| Type | Attached to | Grants? | Notes |
|---|---|---|---|
| AWS managed | users / groups / roles | Yes | Maintained by AWS, often broader than you need |
| Customer managed | users / groups / roles | Yes | Reusable, versioned, what you should mostly write |
| Inline | one user / group / role | Yes | Lives and dies with that identity |
| Resource-based | a resource (S3 bucket, KMS key, role trust policy, ...) | Yes | Has a `Principal`; enables cross-account access |
| Permissions boundary | a user or role | No, only limits | Caps the maximum a delegated admin can grant |
| SCP / RCP (AWS Organizations) | accounts / OUs | No, only limits | Guardrails across many accounts |
| Session policy | an assumed-role session | No, only limits | Passed at `AssumeRole` time |

Realistic identity-based policy for an app that reads and writes reports in one prefix of
one bucket, and must never delete them:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListOnlyTheReportsPrefix",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::raj-demo-reports",
      "Condition": {
        "StringLike": { "s3:prefix": ["reports/*"] }
      }
    },
    {
      "Sid": "ReadWriteReportObjects",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::raj-demo-reports/reports/*"
    },
    {
      "Sid": "NeverDeleteAnything",
      "Effect": "Deny",
      "Action": ["s3:DeleteObject", "s3:DeleteObjectVersion"],
      "Resource": "arn:aws:s3:::raj-demo-reports/*"
    }
  ]
}
```

Note the classic S3 gotcha baked into this: `s3:ListBucket` applies to the **bucket ARN**
(`arn:aws:s3:::bucket`), while object actions apply to **object ARNs**
(`arn:aws:s3:::bucket/*`). Put `ListBucket` on `bucket/*` and listing silently fails with
`AccessDenied`.

## Permissions (how a request is evaluated)

This is the part worth memorising. Simplified, for a request inside one account:

1. **Everything starts as denied** (implicit deny).
2. If **any** applicable policy has an explicit `Deny` that matches, the answer is
   **Deny**. Nothing can override an explicit deny.
3. Guardrails (SCPs, RCPs, permissions boundaries, session policies) must *also* allow the
   action, or the result is an implicit deny. They never grant anything on their own.
4. If an identity-based or resource-based policy has a matching `Allow`, the answer is
   **Allow**.
5. Otherwise it stays at the implicit deny from step 1.

So the priority is: **explicit Deny > explicit Allow > implicit (default) deny**.

Two refinements:

- **Same account**: an `Allow` in *either* the identity policy *or* the resource policy is
  usually enough.
- **Cross-account**: *both* sides must allow. Account B's role needs an identity policy that
  allows `s3:GetObject`, *and* account A's bucket policy must allow account B's role.

## Least privilege

Least privilege means granting only the actions, on only the resources, under only the
conditions that a job actually needs. In practice that's iterative, not a one-time design:

1. Start from an AWS managed policy if you must, in a non-prod account.
2. Use **IAM Access Analyzer policy generation** to build a policy from what the role
   actually did (it reads CloudTrail activity).
3. Narrow `Resource` from `*` to specific ARNs, and add `Condition`s (tags, source VPC, MFA).
4. Use **last accessed** information to remove services and actions nobody has used.

The trap I want to avoid: `"Action": "*"` with `"Resource": "*"` "just to get it working".
That is `AdministratorAccess` under another name, and it tends to stay forever.

## IAM best practices

Condensed from the AWS IAM best-practices page, with my notes:

| Practice | Why it matters |
|---|---|
| Humans use federation / IAM Identity Center with temporary credentials | No long-lived passwords or keys to leak |
| Workloads use IAM roles, never embedded keys | EC2, Lambda, ECS and CI via OIDC all support roles |
| Require MFA | Stolen password alone isn't enough |
| Protect the root user (MFA, no access keys, rarely used) | Root can't be restricted by IAM policies in its account |
| Rotate access keys where long-term keys are unavoidable | Limits the blast radius of a leak |
| Apply least-privilege permissions | Compromise of one identity shouldn't mean compromise of the account |
| Use Access Analyzer to validate policies and find public / cross-account access | Catches mistakes before they ship |
| Regularly remove unused users, roles, keys and permissions | Unused credentials are pure risk |
| Use conditions to further restrict access | e.g. `aws:SecureTransport`, `aws:SourceVpce`, `aws:PrincipalTag` |
| Use SCPs and permissions boundaries as guardrails | Central limits nobody in a member account can bypass |

## Common use cases

- **EC2 instance reading from S3**: a role + instance profile; the SDK picks up temporary
  credentials from the instance metadata service automatically. No keys on disk.
- **CI/CD deploying with Terraform**: GitHub Actions assumes a role via OIDC (trust policy
  above). This ties straight back to the Session 16 GitHub Actions work.
- **Team access**: an `admins` / `developers` / `readonly` split, ideally as Identity Center
  permission sets rather than IAM users and groups.
- **Cross-account access**: a central "tooling" account assumes roles in dev/stage/prod.
- **Break-glass access**: a tightly monitored emergency role, used only during incidents.

## Gotchas worth remembering

- **`iam:PassRole`**: to launch an EC2 instance *with* a role, the caller needs
  `iam:PassRole` on that role, not just `ec2:RunInstances`. This stops people escalating
  privileges by attaching a powerful role to a machine they control.
- **`NotAction` + `Allow`** grants everything *except* the listed actions, which is far
  broader than it reads.
- **Policy size limits** exist (managed and inline policies have character limits), so huge
  lists of ARNs are a design smell; use tags and conditions instead.
- **Eventual consistency**: create-then-use-immediately in scripts can fail; retry.

## Terraform example (for reference)

An EC2 role that can be managed through SSM Session Manager, wrapped in an instance profile.
This is the role the EC2 notes refer to.

```hcl
data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "app" {
  name               = "session18-app-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "app" {
  name = "session18-app-profile"
  role = aws_iam_role.app.name
}
```

## Commands worth knowing

Reference only; not run on this machine.

```bash
# "Who am I right now?" The first command to run when anything is AccessDenied.
aws sts get-caller-identity

# Users, groups, attachments
aws iam list-users --query 'Users[].UserName' --output table
aws iam create-group --group-name developers
aws iam attach-group-policy --group-name developers \
  --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess
aws iam add-user-to-group --group-name developers --user-name raj

# Ask IAM whether a principal would be allowed, without actually doing it
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::123456789012:role/session18-app-role \
  --action-names s3:GetObject s3:DeleteObject \
  --resource-arns arn:aws:s3:::raj-demo-reports/reports/q1.csv

# Account-wide credential report (password age, MFA, key age per user)
aws iam generate-credential-report
aws iam get-credential-report --query Content --output text | base64 --decode
```

## Key takeaways

- IAM is the authorization gate for every AWS API call: global, free, eventually consistent.
- Users and access keys are long-term credentials; roles hand out temporary ones. Prefer
  roles for workloads and federation for humans.
- Evaluation order: **explicit Deny > Allow > implicit deny**. Guardrails (SCPs, RCPs,
  boundaries) only limit; they never grant.
- A role has a trust policy (who can assume it) and permissions policies (what it can do).
  Most "can't assume role" errors are trust policy problems.
- Least privilege is iterative: start narrow, use Access Analyzer and last-accessed data,
  and keep tightening.

## References

- What is IAM? — https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html
- Security best practices in IAM — https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html
- IAM users — https://docs.aws.amazon.com/IAM/latest/UserGuide/id_users.html
- IAM user groups — https://docs.aws.amazon.com/IAM/latest/UserGuide/id_groups.html
- IAM roles — https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html
- Policies and permissions — https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html
- Policy evaluation logic — https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html
- IAM JSON policy element reference — https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements.html
- Create an OIDC identity provider — https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html
