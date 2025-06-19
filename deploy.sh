#!/bin/bash

# US Flag Status API Deployment Script
set -e

PROJECT_NAME="us-flag-status"
ENVIRONMENT="${1:-prod}"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
STACK_NAME="${PROJECT_NAME}-${ENVIRONMENT}"

echo "🇺🇸 Deploying US Flag Status API"
echo "Stack: $STACK_NAME"
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Please run 'aws configure'"
    exit 1
fi

# Create deployment package directory
echo "📦 Creating deployment packages..."
rm -rf dist
mkdir -p dist

# Package API Lambda
echo "  - Packaging API Lambda..."
mkdir -p dist/api
cp src/api/api_handler.py dist/api/
cd dist/api
zip -r ../api-lambda.zip . > /dev/null
cd ../..

# Package Scraper Lambda  
echo "  - Packaging Scraper Lambda..."
mkdir -p dist/scraper
cp src/scraper/scraper_handler.py dist/scraper/
cd dist/scraper
zip -r ../scraper-lambda.zip . > /dev/null
cd ../..

# Upload Lambda packages to S3 (create temp bucket if needed)
LAMBDA_BUCKET="${PROJECT_NAME}-lambda-${ENVIRONMENT}-$(aws sts get-caller-identity --query Account --output text)"
echo "📤 Uploading Lambda packages to S3..."

# Create S3 bucket for Lambda packages if it doesn't exist
if ! aws s3api head-bucket --bucket "$LAMBDA_BUCKET" 2>/dev/null; then
    echo "  - Creating Lambda deployment bucket: $LAMBDA_BUCKET"
    if [ "$REGION" = "us-east-1" ]; then
        aws s3api create-bucket --bucket "$LAMBDA_BUCKET" --region "$REGION"
    else
        aws s3api create-bucket --bucket "$LAMBDA_BUCKET" --region "$REGION" --create-bucket-configuration LocationConstraint="$REGION"
    fi
fi

# Upload packages
aws s3 cp dist/api-lambda.zip "s3://$LAMBDA_BUCKET/api-lambda.zip"
aws s3 cp dist/scraper-lambda.zip "s3://$LAMBDA_BUCKET/scraper-lambda.zip"

# Deploy CloudFormation stack
echo "☁️  Deploying CloudFormation stack..."

aws cloudformation deploy \
    --template-file cloudformation.yaml \
    --stack-name "$STACK_NAME" \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        ProjectName="$PROJECT_NAME" \
        Environment="$ENVIRONMENT" \
        LambdaBucket="$LAMBDA_BUCKET" \
    --tags \
        Type=us-flag-api \
        Created=2025-06-19 \
        Creator=ziegler \
    --region "$REGION"

# Get stack outputs
echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Stack Outputs:"
aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table

# Get API URL
API_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
    --output text)

echo ""
echo "🚀 API Endpoints:"
echo "Current Status: $API_URL/api/v1/status/current"
echo "All Proclamations: $API_URL/api/v1/proclamations"  
echo "Specific Proclamation: $API_URL/api/v1/proclamations/{id}"
echo ""

# Test the API
echo "🧪 Testing API..."
echo "Testing current status endpoint..."
curl -s "$API_URL/api/v1/status/current" | jq '.' || echo "API not ready yet (this is normal for first deployment)"

echo ""
echo "💰 Estimated monthly cost: $7-10 (Bedrock + S3 + Lambda + API Gateway)"
echo ""
echo "To trigger the scraper manually:"
echo "aws lambda invoke --function-name $PROJECT_NAME-scraper-$ENVIRONMENT --payload '{}' /tmp/output.json"
echo ""
echo "To view logs:"
echo "aws logs tail /aws/lambda/$PROJECT_NAME-api-$ENVIRONMENT --follow"
echo "aws logs tail /aws/lambda/$PROJECT_NAME-scraper-$ENVIRONMENT --follow"

# Cleanup
rm -rf dist

echo "🎉 Deployment complete!"