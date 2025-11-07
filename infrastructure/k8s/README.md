# Kubernetes Deployment for DataForge Studio

This directory contains Kubernetes manifests for deploying DataForge Studio on EKS.

## Prerequisites

- EKS cluster provisioned (via Terraform)
- kubectl configured to connect to the cluster
- AWS Load Balancer Controller installed
- Metrics Server installed for HPA

## Quick Start

### 1. Install Dependencies

```bash
# Install AWS Load Balancer Controller
kubectl apply -k "github.com/aws/eks-charts/stable/aws-load-balancer-controller//crds?ref=master"

helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=dataforge-studio-prod \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller

# Install Metrics Server (for HPA)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### 2. Build and Push Docker Image

```bash
# Build image
cd backend
docker build -t dataforge-backend:latest .

# Tag for ECR
docker tag dataforge-backend:latest <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/dataforge-backend:latest

# Login to ECR
aws ecr get-login-password --region <REGION> | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com

# Push
docker push <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/dataforge-backend:latest
```

### 3. Update Configuration

Edit the following files with your values:
- `backend-deployment.yaml`: Update image URI and IAM role ARN
- `ingress.yaml`: Update host, certificate ARN
- `secrets.yaml`: Add actual secrets (or use external-secrets)
- `configmap.yaml`: Update S3 bucket name

### 4. Deploy

```bash
# Apply in order
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
kubectl apply -f redis.yaml  # Skip if using ElastiCache
kubectl apply -f backend-deployment.yaml
kubectl apply -f backend-service.yaml
kubectl apply -f hpa.yaml
kubectl apply -f ingress.yaml
```

### 5. Verify Deployment

```bash
# Check pods
kubectl get pods -n dataforge

# Check services
kubectl get svc -n dataforge

# Check ingress
kubectl get ingress -n dataforge

# Check HPA
kubectl get hpa -n dataforge

# View logs
kubectl logs -f deployment/dataforge-backend -n dataforge

# Get ALB URL
kubectl get ingress dataforge-ingress -n dataforge -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

## Architecture

```
Internet
    ↓
AWS ALB (Ingress)
    ↓
ClusterIP Service (backend-service)
    ↓
Backend Pods (3-20 replicas with HPA)
    ↓
ElastiCache Redis / Pod Redis
    ↓
S3 Bucket (artifacts)
```

## Scaling

### Manual Scaling

```bash
kubectl scale deployment dataforge-backend -n dataforge --replicas=5
```

### Autoscaling

HPA is configured to scale based on:
- CPU utilization (target: 70%)
- Memory utilization (target: 80%)
- Min replicas: 3
- Max replicas: 20

## Monitoring

### View Metrics

```bash
# Pod metrics
kubectl top pods -n dataforge

# Node metrics
kubectl top nodes
```

### View Logs

```bash
# All backend logs
kubectl logs -l app=dataforge-backend -n dataforge --tail=100 -f

# Specific pod
kubectl logs <pod-name> -n dataforge -f
```

### CloudWatch Logs

Logs are automatically sent to CloudWatch if Container Insights is enabled:

```bash
# Enable Container Insights
aws eks update-cluster-config \
  --name dataforge-studio-prod \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

## Troubleshooting

### Pods Not Starting

```bash
kubectl describe pod <pod-name> -n dataforge
kubectl logs <pod-name> -n dataforge
```

### HPA Not Scaling

```bash
kubectl describe hpa dataforge-backend-hpa -n dataforge

# Check metrics server
kubectl get deployment metrics-server -n kube-system
kubectl logs -n kube-system -l k8s-app=metrics-server
```

### Ingress Not Working

```bash
kubectl describe ingress dataforge-ingress -n dataforge

# Check ALB controller
kubectl logs -n kube-system deployment/aws-load-balancer-controller
```

### Redis Connection Issues

```bash
# Test from a pod
kubectl run -it --rm debug --image=redis:7-alpine --restart=Never -- redis-cli -h dataforge-redis ping
```

## Security

### Secrets Management

For production, use AWS Secrets Manager with external-secrets operator:

```bash
# Install external-secrets
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets -n external-secrets-system --create-namespace
```

### Network Policies

```bash
kubectl apply -f network-policies.yaml
```

### Pod Security Standards

```bash
kubectl label namespace dataforge pod-security.kubernetes.io/enforce=restricted
```

## Updates and Rollbacks

### Rolling Update

```bash
# Update image
kubectl set image deployment/dataforge-backend backend=<NEW_IMAGE> -n dataforge

# Monitor rollout
kubectl rollout status deployment/dataforge-backend -n dataforge
```

### Rollback

```bash
# View history
kubectl rollout history deployment/dataforge-backend -n dataforge

# Rollback to previous
kubectl rollout undo deployment/dataforge-backend -n dataforge

# Rollback to specific revision
kubectl rollout undo deployment/dataforge-backend -n dataforge --to-revision=2
```

## Cleanup

```bash
kubectl delete -f ingress.yaml
kubectl delete -f hpa.yaml
kubectl delete -f backend-service.yaml
kubectl delete -f backend-deployment.yaml
kubectl delete -f redis.yaml
kubectl delete -f secrets.yaml
kubectl delete -f configmap.yaml
kubectl delete -f namespace.yaml
```

## Production Checklist

- [ ] Update all placeholder values in manifests
- [ ] Use external-secrets or AWS Secrets Manager for secrets
- [ ] Configure proper DNS for ingress hostname
- [ ] Set up SSL certificate in ACM
- [ ] Configure Redis using ElastiCache (not pod)
- [ ] Enable Container Insights for monitoring
- [ ] Set up CloudWatch alarms
- [ ] Configure backup strategies for Redis
- [ ] Implement network policies
- [ ] Set resource limits appropriately
- [ ] Configure pod disruption budgets
- [ ] Set up CI/CD pipeline for deployments

