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
        },
        {
            "Effect": "Allow",
            "Action": [
                "iam:PassRole"
            ],
            "Resource": "arn:aws:iam::*:role/AppRunnerECRAccessRole"
        }
    ]
}
```

## App Runner Service Role

App Runner also needs a service role to access ECR. Create an IAM role with:

1. **Trust Policy** (who can assume this role):
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "build.apprunner.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```

2. **Attach the AWS managed policy**: `AmazonAppRunnerServicePolicyForECRAccess`

## GitHub Secrets Required

- `AWS_ACCOUNT_ID`: Your AWS account ID
- `AWS_ROLE_TO_ASSUME`: ARN of the IAM role for GitHub Actions (with the policy above)

## Service Names

The workflow creates these App Runner services:
- Backend: `light-score-backend-staging`
- Frontend: `light-score-frontend-staging`
