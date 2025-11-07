# DataForge Studio - Deployment Guide

## Deployment Options

DataForge Studio can be deployed in multiple environments:

1. **Local Development** - Docker Compose
2. **Cloud Development** - AWS EKS (Dev)
3. **Production** - AWS EKS (Prod) with full HA

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured
- Docker and Docker Compose
- kubectl
- Terraform >= 1.5
- Python 3.11+
- Node.js 18+ (for frontend)

## Quick Start (Local)

```bash
# Clone repository
git clone <repo-url>
cd dataforge-studio

# Set up environment
make setup

# Install spacy model
make install-spacy

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run with Docker Compose
docker-compose up -d

# Access API
curl http://localhost:8000/healthz
```

## AWS Production Deployment

### Step 1: Prerequisites

```bash
# Install required tools
brew install terraform kubectl helm

# Configure AWS CLI
aws configure

# Verify access
aws sts get-caller-identity
```

### Step 2: Deploy Infrastructure

```bash
cd infrastructure/terraform

# Initialize Terraform
terraform init

# Create environment file
cat > environments/prod.tfvars << EOF
environment         = "prod"
aws_region          = "us-east-1"
eks_node_desired_size = 3
eks_node_min_size     = 2
eks_node_max_size     = 10
redis_node_type       = "cache.r6g.large"
redis_num_cache_nodes = 3
EOF

# Plan
terraform plan -var-file=environments/prod.tfvars

# Apply
terraform apply -var-file=environments/prod.tfvars
```

### Step 3: Configure kubectl

```bash
# Update kubeconfig
aws eks update-kubeconfig --region us-east-1 --name dataforge-studio-prod

# Verify connection
kubectl get nodes
```

### Step 4: Install Dependencies

```bash
# AWS Load Balancer Controller
kubectl apply -k "github.com/aws/eks-charts/stable/aws-load-balancer-controller//crds?ref=master"

helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=dataforge-studio-prod \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller

# Metrics Server
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# External Secrets (Recommended)
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  -n external-secrets-system \
  --create-namespace
```

### Step 5: Build and Push Image

```bash
# Get ECR repository URI from Terraform
ECR_REPO=$(terraform output -raw ecr_repository_url)
REGION=$(terraform output -raw aws_region)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Build image
cd ../../backend
docker build -t dataforge-backend:latest .

# Tag for ECR
docker tag dataforge-backend:latest ${ECR_REPO}:latest
docker tag dataforge-backend:latest ${ECR_REPO}:v1.0.0

# Login to ECR
aws ecr get-login-password --region ${REGION} | \
  docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com

# Push
docker push ${ECR_REPO}:latest
docker push ${ECR_REPO}:v1.0.0
```

### Step 6: Update Kubernetes Manifests

```bash
cd ../infrastructure/k8s

# Update deployment with your values
sed -i '' "s/<ACCOUNT_ID>/${ACCOUNT_ID}/g" backend-deployment.yaml
sed -i '' "s/<REGION>/${REGION}/g" backend-deployment.yaml

# Update secrets (use AWS Secrets Manager in production)
kubectl create secret generic dataforge-secrets \
  -n dataforge \
  --from-literal=api-key=<YOUR_API_KEY> \
  --from-literal=langsmith-api-key=<YOUR_LANGSMITH_KEY>
```

### Step 7: Deploy Application

```bash
# Apply manifests
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f backend-deployment.yaml
kubectl apply -f backend-service.yaml
kubectl apply -f hpa.yaml
kubectl apply -f ingress.yaml
```

### Step 8: Verify Deployment

```bash
# Check pods
kubectl get pods -n dataforge

# Check services
kubectl get svc -n dataforge

# Check ingress
kubectl get ingress -n dataforge

# Get ALB URL
ALB_URL=$(kubectl get ingress dataforge-ingress -n dataforge \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo "API URL: https://${ALB_URL}"

# Test health endpoint
curl https://${ALB_URL}/healthz
```

## Configuration

### Environment Variables

Key environment variables for production:

```bash
# AWS
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=<from-iam-role>
AWS_SECRET_ACCESS_KEY=<from-iam-role>

# LLM
LLM_PROVIDER=bedrock
LLM_MODEL=anthropic.claude-3-5-haiku-20241022:0
LLM_TEMPERATURE=0.7

# LangSmith
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=<your-key>
LANGCHAIN_PROJECT=dataforge-studio-prod

# Storage
S3_BUCKET=dataforge-studio-prod-artifacts
USE_S3=true

# Redis
REDIS_URL=redis://dataforge-redis:6379
USE_REDIS=true

# Security
API_KEY=<secure-key>
```

### Secrets Management

**Development**: Use Kubernetes secrets
**Production**: Use AWS Secrets Manager + External Secrets Operator

```yaml
# external-secret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: dataforge-secrets
  namespace: dataforge
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: dataforge-secrets
  data:
  - secretKey: api-key
    remoteRef:
      key: dataforge/api-key
  - secretKey: langsmith-api-key
    remoteRef:
      key: dataforge/langsmith-key
```

## Monitoring

### CloudWatch Container Insights

```bash
# Enable Container Insights
aws eks update-cluster-config \
  --name dataforge-studio-prod \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

### LangSmith Dashboard

1. Create LangSmith account at https://smith.langchain.com
2. Create project: `dataforge-studio-prod`
3. Get API key
4. Set in secrets: `LANGCHAIN_API_KEY`

### Custom Metrics

```python
# CloudWatch custom metrics
import boto3

cloudwatch = boto3.client('cloudwatch')

cloudwatch.put_metric_data(
    Namespace='DataForge',
    MetricData=[
        {
            'MetricName': 'JobsCompleted',
            'Value': 1,
            'Unit': 'Count'
        }
    ]
)
```

## Scaling

### Manual Scaling

```bash
# Scale deployment
kubectl scale deployment dataforge-backend -n dataforge --replicas=10

# Scale EKS nodes
aws eks update-nodegroup-config \
  --cluster-name dataforge-studio-prod \
  --nodegroup-name dataforge-studio-prod-node-group \
  --scaling-config minSize=5,maxSize=20,desiredSize=10
```

### Autoscaling

HPA is pre-configured. To adjust:

```yaml
# hpa.yaml
spec:
  minReplicas: 5
  maxReplicas: 30
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        averageUtilization: 60  # Lower = more aggressive scaling
```

## Updates

### Rolling Update

```bash
# Update image
kubectl set image deployment/dataforge-backend \
  backend=${ECR_REPO}:v1.1.0 \
  -n dataforge

# Monitor
kubectl rollout status deployment/dataforge-backend -n dataforge
```

### Blue-Green Deployment

```bash
# Create new deployment
kubectl apply -f backend-deployment-v2.yaml

# Test new version
kubectl port-forward deployment/dataforge-backend-v2 8001:8000 -n dataforge

# Switch traffic
kubectl patch service dataforge-backend -n dataforge \
  -p '{"spec":{"selector":{"version":"v2"}}}'

# Rollback if needed
kubectl patch service dataforge-backend -n dataforge \
  -p '{"spec":{"selector":{"version":"v1"}}}'
```

## Backup and Recovery

### S3 Backup

S3 versioning is enabled by default. To backup:

```bash
# Sync to backup bucket
aws s3 sync s3://dataforge-studio-prod-artifacts \
  s3://dataforge-studio-prod-backup \
  --region us-east-1
```

### Redis Backup

ElastiCache Redis has automatic snapshots (5 days retention).

Manual backup:

```bash
aws elasticache create-snapshot \
  --cache-cluster-id dataforge-studio-prod-redis \
  --snapshot-name manual-backup-$(date +%Y%m%d)
```

### Disaster Recovery

1. **RTO** (Recovery Time Objective): < 1 hour
2. **RPO** (Recovery Point Objective): < 1 hour

Recovery procedure:
```bash
# 1. Deploy infrastructure (Terraform)
terraform apply

# 2. Restore S3 from backup
aws s3 sync s3://backup-bucket s3://new-bucket

# 3. Restore Redis snapshot
aws elasticache restore-cache-cluster-from-snapshot \
  --cache-cluster-id new-cluster \
  --snapshot-name backup-name

# 4. Deploy application
kubectl apply -f k8s/
```

## Troubleshooting

### Pods Crash Looping

```bash
# Check logs
kubectl logs -f deployment/dataforge-backend -n dataforge

# Describe pod
kubectl describe pod <pod-name> -n dataforge

# Common issues:
# - Missing secrets
# - Invalid AWS credentials
# - Insufficient memory/CPU
# - Network connectivity
```

### High Latency

```bash
# Check HPA status
kubectl get hpa -n dataforge

# Check pod metrics
kubectl top pods -n dataforge

# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/EKS \
  --metric-name pod_cpu_utilization \
  --dimensions Name=ClusterName,Value=dataforge-studio-prod \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T23:59:59Z \
  --period 300 \
  --statistics Average
```

### Database Connection Issues

```bash
# Test Redis
kubectl run -it --rm redis-test --image=redis:7-alpine --restart=Never \
  -- redis-cli -h dataforge-redis ping

# Check ElastiCache
aws elasticache describe-cache-clusters \
  --cache-cluster-id dataforge-studio-prod-redis \
  --show-cache-node-info
```

## Cost Optimization

### Development Environment

- Use Spot Instances for EKS nodes
- Scale down outside business hours
- Use t3.medium instances
- Single Redis instance

```bash
# Scheduled scaling (example with kube-downscaler)
kubectl annotate deployment dataforge-backend -n dataforge \
  downscaler/uptime='Mon-Fri 09:00-18:00 America/New_York'
```

### Production Environment

- Use Reserved Instances (1-year commitment)
- Enable S3 Intelligent Tiering
- Use ElastiCache Reserved Nodes
- Implement request caching

Estimated costs:
- **Dev**: ~$150-200/month
- **Prod**: ~$800-1200/month

## Security Checklist

- [ ] API keys rotated regularly
- [ ] TLS certificates valid and auto-renewing
- [ ] Security groups minimal
- [ ] IAM roles least privilege
- [ ] S3 buckets not public
- [ ] Redis encryption enabled
- [ ] Secrets in Secrets Manager
- [ ] CloudWatch logging enabled
- [ ] Network policies applied
- [ ] Pod security policies enforced
- [ ] Container images scanned
- [ ] Dependencies updated

## Support

For issues:
1. Check logs: `kubectl logs`
2. Check CloudWatch
3. Check LangSmith traces
4. GitHub Issues
5. Email: support@dataforge-studio.example.com

