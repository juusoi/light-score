#!/bin/bash
# filepath: scripts/setup-aws.sh

set -euo pipefail

# Configuration
REGION="eu-north-1"
ROLE_NAME="GitHubActionsRole"
POLICY_NAME="LightScoreDeploymentPolicy"
REPO_OWNER="juusoi"
REPO_NAME="light-score"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

title() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &>/dev/null; then
    error "AWS CLI not configured. Run 'aws configure' first."
    exit 1
fi

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
log "AWS Account ID: $ACCOUNT_ID"

title "Setting up IAM Role and Policy for GitHub Actions"

# Create IAM policy for deployment
log "Creating IAM policy: $POLICY_NAME"
cat > /tmp/deployment-policy.json << EOF
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
EOF

# Create or update the policy
if aws iam get-policy --policy-arn "arn:aws:iam::$ACCOUNT_ID:policy/$POLICY_NAME" &>/dev/null; then
    log "Policy $POLICY_NAME already exists, updating..."
    aws iam create-policy-version \
        --policy-arn "arn:aws:iam::$ACCOUNT_ID:policy/$POLICY_NAME" \
        --policy-document file:///tmp/deployment-policy.json \
        --set-as-default
else
    log "Creating new policy: $POLICY_NAME"
    aws iam create-policy \
        --policy-name "$POLICY_NAME" \
        --policy-document file:///tmp/deployment-policy.json \
        --description "Policy for GitHub Actions to deploy Light Score app"
fi

# Create trust policy for GitHub OIDC
log "Creating trust policy for GitHub OIDC"
cat > /tmp/trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::$ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:$REPO_OWNER/$REPO_NAME:*"
        }
      }
    }
  ]
}
EOF

# Create or update the role
if aws iam get-role --role-name "$ROLE_NAME" &>/dev/null; then
    log "Role $ROLE_NAME already exists, updating trust policy..."
    aws iam update-assume-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-document file:///tmp/trust-policy.json
else
    log "Creating new role: $ROLE_NAME"
    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document file:///tmp/trust-policy.json \
        --description "Role for GitHub Actions to deploy Light Score app"
fi

# Attach policy to role
log "Attaching policy to role"
aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn "arn:aws:iam::$ACCOUNT_ID:policy/$POLICY_NAME"

title "Setting up GitHub OIDC Provider"

# Check if OIDC provider exists
if aws iam get-open-id-connect-provider \
    --open-id-connect-provider-arn "arn:aws:iam::$ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com" &>/dev/null; then
    log "GitHub OIDC provider already exists"
else
    log "Creating GitHub OIDC provider"
    aws iam create-open-id-connect-provider \
        --url "https://token.actions.githubusercontent.com" \
        --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1" \
        --client-id-list "sts.amazonaws.com"
fi

title "Creating ECR Repositories"

# Create ECR repositories if they don't exist
for app in "light-score-backend" "light-score-frontend"; do
    if aws ecr describe-repositories --repository-names "$app" --region "$REGION" &>/dev/null; then
        log "ECR repository $app already exists"
    else
        log "Creating ECR repository: $app"
        aws ecr create-repository \
            --repository-name "$app" \
            --region "$REGION"
    fi
done

# Clean up temporary files
rm -f /tmp/deployment-policy.json /tmp/trust-policy.json

title "Setup Complete!"

echo -e "\n${GREEN}✅ AWS setup completed successfully!${NC}\n"

echo -e "${BLUE}GitHub Secrets to add:${NC}"
echo -e "  ${YELLOW}AWS_ACCOUNT_ID${NC}: $ACCOUNT_ID"
echo -e "  ${YELLOW}AWS_ROLE_TO_ASSUME${NC}: arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME"

echo -e "\n${BLUE}Next steps:${NC}"
echo -e "1. Add the GitHub secrets above to your repository"
echo -e "2. Merge your PR to main branch"
echo -e "3. Run the 'Build and Deploy to AWS Staging' workflow"
echo -e "4. Your app will be available at the App Runner URLs shown in the workflow output"

echo -e "\n${BLUE}ECR Repositories created:${NC}"
echo -e "  • ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/light-score-backend"
echo -e "  • ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/light-score-frontend"

echo -e "\n${GREEN}🚀 Ready to deploy!${NC}"