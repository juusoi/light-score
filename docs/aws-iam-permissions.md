<!--
NOTE: This file is written under a "treat everything as public" policy.
Do NOT add real account IDs, bucket names, table names, ARNs, IPs, or secrets.
All concrete identifiers are parameterised with ALL_CAPS placeholders.
-->

# AWS IAM Permissions (Terraform + Lightsail via GitHub Actions OIDC)

Terraform + Lightsail deploy via OIDC. Minimal combined policy.

---

## 1. Trust Policy (GitHub OIDC)

Attach this **trust policy** to the IAM Role you want GitHub Actions to assume. Replace:

- `ACCOUNT_ID` with your 12‑digit AWS account id
- `ORG` / `REPO` with your GitHub org & repository
- Optionally narrow `sub` further to specific workflow run IDs using `:workflow/` patterns

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": [
            "repo:ORG/REPO:ref:refs/heads/main"
          ]
        }
      }
    }
  ]
}
```

Add more `sub` patterns for other refs as needed.

---

## 2. Combined Least‑Privilege Policy

Parameters: `TF_STATE_BUCKET`, `TF_STATE_PREFIX`, `TF_LOCKS_TABLE`, `AWS_REGION`, `ACCOUNT_ID`, optional `LIGHTSAIL_SERVICE_NAME`.

The Terraform backend example stores state at `TF_STATE_PREFIX/terraform.tfstate`.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "TerraformStateListBucket",
      "Effect": "Allow",
      "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
      "Resource": "arn:aws:s3:::TF_STATE_BUCKET",
      "Condition": { "StringLike": { "s3:prefix": ["TF_STATE_PREFIX*"] } }
    },
    {
      "Sid": "TerraformStateObjectsRW",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:AbortMultipartUpload",
        "s3:ListMultipartUploadParts"
      ],
      "Resource": "arn:aws:s3:::TF_STATE_BUCKET/TF_STATE_PREFIX*"
    },
    {
      "Sid": "TerraformDynamoLocking",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:DeleteItem",
        "dynamodb:UpdateItem",
        "dynamodb:DescribeTable"
      ],
      "Resource": "arn:aws:dynamodb:AWS_REGION:ACCOUNT_ID:table/TF_LOCKS_TABLE"
    },
    {
      "Sid": "LightsailManageContainerService",
      "Effect": "Allow",
      "Action": [
        "lightsail:CreateContainerService",
        "lightsail:UpdateContainerService",
        "lightsail:DeleteContainerService",
        "lightsail:GetContainerServices",
        "lightsail:GetContainerServiceDeployments",
        "lightsail:GetContainerServicePowers",
        "lightsail:CreateContainerServiceDeployment",
        "lightsail:PushContainerImage",
        "lightsail:GetContainerImages"
      ],
      "Resource": "*"
    },
    {
      "Sid": "LightsailCertificateManagement",
      "Effect": "Allow",
      "Action": [
        "lightsail:CreateCertificate",
        "lightsail:GetCertificates",
        "lightsail:DeleteCertificate"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ReadOperationsForDebug",
      "Effect": "Allow",
      "Action": ["lightsail:GetOperations", "lightsail:GetOperation"],
      "Resource": "*"
    }
  ]
}
```

`PushContainerImage` uses internal registry (no ECR perms needed).

---

## 3. Environment Variables / Secrets

Secrets: `AWS_ROLE_TO_ASSUME` (required), `AWS_ACCOUNT_ID` (optional).

---

## 4. Terraform Backend Recap

Sample `terraform/backend.tf` (replace placeholders):

```hcl
terraform {
  backend "s3" {
    bucket         = "TF_STATE_BUCKET"
    key            = "TF_STATE_PREFIX/terraform.tfstate"
    region         = "AWS_REGION"
    dynamodb_table = "TF_LOCKS_TABLE"
    encrypt        = true
  }
}
```

Add environments: duplicate statements with new prefix & lock table.

---

## 5. Lightsail Internal Networking

`BACKEND_URL`: `http://LIGHTSAIL_SERVICE_NAME.service.local:8000`.

---

## 6. Quick Verification Script

Quick check:

```bash
aws sts get-caller-identity
aws s3 ls s3://TF_STATE_BUCKET/TF_STATE_PREFIX --region AWS_REGION
aws dynamodb describe-table --table-name TF_LOCKS_TABLE --region AWS_REGION
aws lightsail get-container-services --region eu-north-1 --query 'containerServices[].serviceName'
```
