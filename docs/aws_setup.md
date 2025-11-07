# AWS Setup Guide

## Local Development Setup (IAM User)

### 1. Create IAM User

1. **Go to AWS Console** → IAM → Users → "Create user"

2. **User details:**
   - Username: `dataforge-studio-dev`
   - Enable: ✅ "Programmatic access" (AWS access key)

3. **Set permissions** - Attach these policies:
   - `AmazonBedrockFullAccess` (for Claude Haiku 4.5)
   - `AmazonS3FullAccess` (for artifact storage)
   - `AmazonElastiCacheFullAccess` (for Redis, optional)
   
   **OR create a custom policy** (more secure):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BedrockAccess",
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:ListFoundationModels",
                "bedrock:GetFoundationModel"
            ],
            "Resource": "*"
        },
        {
            "Sid": "S3Access",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::dataforge-studio-*",
                "arn:aws:s3:::dataforge-studio-*/*"
            ]
        },
        {
            "Sid": "CloudWatchLogs",
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:log-group:/dataforge-studio/*"
        }
    ]
}
```

4. **Download credentials**
   - Save the `Access Key ID` and `Secret Access Key`
   - ⚠️ You won't be able to see the secret key again!

### 2. Configure Local Environment

Add to your `.env` file:

```bash
# AWS Configuration
AWS_REGION=us-east-1  # or your preferred region
AWS_ACCESS_KEY_ID=AKIA...your-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key

# Bedrock Configuration
LLM_PROVIDER=bedrock
LLM_MODEL=anthropic.claude-3-5-haiku-20241022:0
```

### 3. Verify Bedrock Access

**Check if Claude Haiku 4.5 is available in your region:**

```bash
aws bedrock list-foundation-models \
  --region us-east-1 \
  --query "modelSummaries[?contains(modelId, 'claude-3-5-haiku')].{ModelId:modelId, ModelName:modelName}" \
  --output table
```

**Important:** Claude models are available in these regions:
- ✅ `us-east-1` (N. Virginia)
- ✅ `us-west-2` (Oregon)
- ✅ `eu-central-1` (Frankfurt)
- ✅ `ap-southeast-2` (Sydney)

If not available, you need to:
1. Go to AWS Console → Bedrock → Model access
2. Click "Manage model access"
3. Enable "Claude 3.5 Haiku"
4. Wait for approval (usually instant)

### 4. Test Connection

```bash
# Activate conda environment
conda activate dataforge-studio

# Test AWS connection
python -c "
import boto3
client = boto3.client('bedrock', region_name='us-east-1')
models = client.list_foundation_models()
print('✅ AWS Bedrock connection successful!')
"
```

---

## Production Setup (IAM Roles for EKS) - FOR LATER

When you deploy to EKS, you'll use **IAM Roles for Service Accounts (IRSA)** instead of access keys. This is more secure.

### Why IAM Roles for Production?

- ✅ No hardcoded credentials
- ✅ Automatic credential rotation
- ✅ Fine-grained permissions per pod
- ✅ Better audit trail

### Quick Overview (detailed setup in deployment.md)

1. **Create IAM Role for EKS Service Account**
   ```bash
   eksctl create iamserviceaccount \
     --name dataforge-studio-sa \
     --namespace dataforge-studio \
     --cluster dataforge-cluster \
     --attach-policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess \
     --approve
   ```

2. **Pod will automatically assume this role** - No keys needed!

---

## Security Best Practices

### For Local Development

1. **Use AWS CLI profiles** (alternative to .env):
   ```bash
   # Configure profile
   aws configure --profile dataforge-studio
   
   # Use in your .env
   AWS_PROFILE=dataforge-studio
   ```

2. **Rotate keys regularly**:
   - Create new keys every 90 days
   - Delete old keys after rotation

3. **Never commit .env to git**:
   - Already in .gitignore ✅
   - Use `.env.example` as template only

4. **Use least privilege**:
   - Only grant permissions you actually need
   - Start restrictive, expand as needed

### For Production

1. **Use IAM Roles, not Users**
2. **Enable CloudTrail logging**
3. **Use AWS Secrets Manager** for sensitive data
4. **Enable MFA for IAM users**

---

## Troubleshooting

### "AccessDeniedException: User is not authorized"

**Solution:** Enable Bedrock model access
1. AWS Console → Bedrock → Model access
2. Enable Claude models
3. Wait a few minutes for activation

### "Could not connect to the endpoint URL"

**Solution:** Check region
- Bedrock is not available in all regions
- Use `us-east-1`, `us-west-2`, or `eu-central-1`

### "Signature expired"

**Solution:** Check system time
```bash
# On macOS
sudo sntp -sS time.apple.com
```

### "Invalid access key"

**Solution:** Regenerate keys
1. AWS Console → IAM → Users → Security credentials
2. "Create access key"
3. Update .env file

---

## Cost Estimation

### Claude Haiku 4.5 Pricing (as of 2024)

- **Input:** ~$0.25 per 1M tokens
- **Output:** ~$1.25 per 1M tokens

### Typical Usage

- Schema generation: ~2,000 tokens per request = $0.003
- Document generation: ~3,000 tokens per request = $0.005
- **Estimated cost for testing:** $1-5/month

### Cost Control

1. **Set billing alerts:**
   ```bash
   aws budgets create-budget \
     --account-id YOUR_ACCOUNT_ID \
     --budget file://budget.json
   ```

2. **Use LangSmith** to monitor token usage

3. **Implement rate limiting** in production

---

## Quick Start Checklist

- [ ] Create IAM user `dataforge-studio-dev`
- [ ] Attach `AmazonBedrockFullAccess` policy
- [ ] Download access keys
- [ ] Add credentials to `.env` file
- [ ] Enable Bedrock model access (Claude 3.5 Haiku)
- [ ] Verify connection with test script
- [ ] Run `python backend/test_zero_shot.py`

---

## Next Steps

1. ✅ Set up IAM user (this guide)
2. ✅ Configure `.env` file
3. ✅ Test zero-shot generation
4. 🔜 Deploy to EKS (see `docs/deployment.md`)
5. 🔜 Set up IRSA for production

