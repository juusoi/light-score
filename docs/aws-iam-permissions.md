# AWS IAM Permissions for GitHub Actions

The GitHub Actions workflow requires an IAM role with the following permissions for Terraform and Lightsail deployment.

## Required IAM Policy

Create an IAM policy with these permissions and attach it to the role that GitHub Actions assumes:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "TerraformStateManagement",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::tfstate-lightscore-eun1",
        "arn:aws:s3:::tfstate-lightscore-eun1/*"
      ]
    },
    {
      "Sid": "TerraformStateLocking",
      "Effect": "Allow",
      "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem"],
      "Resource": "arn:aws:dynamodb:eu-north-1:*:table/tf-locks-lightscore-eun1"
    },
    {
      "Sid": "LightsailManagement",
      "Effect": "Allow",
      "Action": [
        "lightsail:CreateContainerService",
        "lightsail:UpdateContainerService",
        "lightsail:DeleteContainerService",
        "lightsail:GetContainerServices",
        "lightsail:GetContainerServiceDeployments",
        "lightsail:CreateContainerServiceDeployment",
        "lightsail:PushContainerImage",
        "lightsail:GetContainerImages"
      ],
      "Resource": "*"
    }
  ]
}
```

## App Runner ECR Access

App Runner automatically handles ECR access when using ECR images. **No manual service role setup required.**

The IAM permissions above are sufficient for the GitHub Actions workflow to create and manage App Runner services that pull from ECR.

## GitHub Secrets Required

- `AWS_ACCOUNT_ID`: Your AWS account ID
- `AWS_ROLE_TO_ASSUME`: ARN of the IAM role for GitHub Actions (with the policy above)

## Service Names

The workflow creates these App Runner services:

- Backend: `light-score-backend-staging`
- Frontend: `light-score-frontend-staging`
