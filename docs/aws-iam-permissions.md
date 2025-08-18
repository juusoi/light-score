# AWS IAM Permissions for GitHub Actions

The GitHub Actions workflow requires an IAM role with the following permissions to build images and deploy to App Runner.

## Required IAM Policy

Create an IAM policy with these permissions and attach it to the role that GitHub Actions assumes:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:DescribeRepositories",
        "ecr:CreateRepository",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "apprunner:CreateService",
        "apprunner:UpdateService",
        "apprunner:DescribeService",
        "apprunner:ListServices"
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
