# DataForge Studio - Terraform Infrastructure

This directory contains Terraform configuration for deploying DataForge Studio infrastructure on AWS.

## Prerequisites

- Terraform >= 1.5
- AWS CLI configured with appropriate credentials
- kubectl installed

## Architecture

The infrastructure includes:

- **VPC** with public and private subnets across 3 AZs
- **EKS Cluster** (Kubernetes v1.28) with managed node groups
- **S3 Bucket** for artifact storage with encryption and lifecycle policies
- **ElastiCache Redis** for caching and session state
- **KMS Key** for encryption
- **CloudWatch Alarms** and SNS for monitoring

## Setup

### 1. Initialize Terraform

```bash
cd infrastructure/terraform
terraform init
```

### 2. Create State Backend (First Time Only)

```bash
# Create S3 bucket for state
aws s3 mb s3://dataforge-terraform-state --region us-east-1

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name dataforge-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### 3. Plan Infrastructure

```bash
terraform plan -var-file=environments/dev.tfvars
```

### 4. Apply Infrastructure

```bash
terraform apply -var-file=environments/dev.tfvars
```

## Configuration

### Environment Variables

Create environment-specific `.tfvars` files in `environments/` directory:

**environments/dev.tfvars:**

```hcl
environment         = "dev"
aws_region          = "us-east-1"
eks_node_desired_size = 2
eks_node_min_size     = 1
eks_node_max_size     = 5
redis_node_type       = "cache.t3.micro"
```

**environments/prod.tfvars:**

```hcl
environment         = "prod"
aws_region          = "us-east-1"
eks_node_desired_size = 3
eks_node_min_size     = 2
eks_node_max_size     = 10
redis_node_type       = "cache.r6g.large"
redis_num_cache_nodes = 3
```

## Post-Deployment

### Configure kubectl

```bash
aws eks update-kubeconfig --region us-east-1 --name dataforge-studio-dev
```

### Verify Cluster

```bash
kubectl get nodes
kubectl get pods --all-namespaces
```

### Get Outputs

```bash
terraform output
```

## Resource Costs (Estimated)

**Development Environment (~$150-200/month):**

- EKS Cluster: ~$75/month
- EC2 Nodes (2x t3.medium): ~$60/month
- ElastiCache Redis (t3.micro): ~$15/month
- NAT Gateways (3x): ~$100/month
- S3 Storage: ~$5/month (1TB)
- Data Transfer: Variable

**Production Environment (~$800-1200/month):**

- EKS Cluster: ~$75/month
- EC2 Nodes (3-10x t3.large): ~$300-1000/month
- ElastiCache Redis (r6g.large, 3 nodes): ~$400/month
- NAT Gateways (3x): ~$100/month
- S3 Storage: ~$25/month (5TB)
- Data Transfer: Variable

## Cleanup

```bash
terraform destroy -var-file=environments/dev.tfvars
```

⚠️ **Warning**: This will delete all resources including data in S3 and Redis.

## Security Considerations

- All data is encrypted at rest using KMS
- Redis uses transit encryption
- S3 buckets have public access blocked
- EKS uses private subnets for nodes
- IAM roles follow least privilege principle
- VPC endpoints for AWS services
- CloudWatch logging enabled

## Troubleshooting

### EKS Cluster Not Accessible

```bash
aws eks describe-cluster --name dataforge-studio-dev --region us-east-1
```

### Check Node Group Status

```bash
aws eks describe-nodegroup \
  --cluster-name dataforge-studio-dev \
  --nodegroup-name dataforge-studio-dev-node-group \
  --region us-east-1
```

### Redis Connection Issues

```bash
# Test from within VPC
redis-cli -h <redis-endpoint> -p 6379 --tls
```

## Support

For issues, please create a GitHub issue or contact the DevOps team.
