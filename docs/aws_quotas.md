# AWS Bedrock Service Quotas Guide

## Understanding Your Current Quotas

Based on your quota display, here's what each quota means and which ones to increase:

### Current Quota Status

| Quota Name | Current | Max Available | Recommendation |
|------------|---------|---------------|----------------|
| **Cross-region requests/min** | 2 | 125 | ⚠️ **INCREASE THIS** |
| **Cross-region tokens/min** | 500,000 | 500,000 | ✅ Already at max |
| **Global cross-region requests/min** | 3 | 250 | ⚠️ **INCREASE THIS** |
| **Global cross-region tokens/day** | 54M | 1.44B | ✅ Sufficient for now |
| **Global cross-region tokens/min** | 1M | 1M | ✅ Already at max |

---

## Which Quotas to Increase

### 🔴 **Priority 1: Cross-region model inference requests per minute**

**Current:** 2 requests/minute  
**Max Available:** 125 requests/minute  
**Recommended:** **20-50 requests/minute** for development, **100+ for production**

**Why this matters:**
- Your schema agent makes **5-6 LLM calls per schema generation** (analyze, suggest columns, infer relationships, validate, normalize)
- At 2 RPM, you can only process **1 schema every 2-3 minutes**
- This is the **primary bottleneck** causing your throttling issues

**How to increase:**
1. Go to AWS Console → Service Quotas
2. Search for "Bedrock"
3. Find "Cross-region model inference requests per minute for Anthropic Claude Haiku 4.5"
4. Click "Request quota increase"
5. Enter **20** (for testing) or **50** (for heavier use)
6. Submit request (usually approved within minutes to hours)

---

### 🟡 **Priority 2: Global cross-region model inference requests per minute**

**Current:** 3 requests/minute  
**Max Available:** 250 requests/minute  
**Recommended:** **50-100 requests/minute**

**Why this matters:**
- This is a **higher-level quota** that affects all your cross-region inference calls
- Should be at least **2-3x your per-model quota** to avoid conflicts
- Important if you plan to use multiple models (e.g., Haiku + Sonnet)

**How to increase:**
1. Same process as above
2. Find "Global cross-region model inference requests per minute"
3. Request **50-100 RPM**

---

### ✅ **Quotas Already Optimized**

These quotas are already at their maximum or sufficient:

#### 1. **Cross-region tokens per minute: 500,000**
- **Status:** Already at maximum
- **Sufficient for:** ~10-15 schema generations per minute (based on typical token usage)
- **No action needed** unless you frequently generate very large schemas

#### 2. **Global cross-region tokens per minute: 1,000,000**
- **Status:** Already at maximum
- **Sufficient for:** Most workloads
- **No action needed**

#### 3. **Global cross-region tokens per day: 54,000,000**
- **Status:** Well below maximum (1.44B available)
- **Sufficient for:** Thousands of schema generations per day
- **No action needed**

---

## How to Request Quota Increases

### Step-by-Step Guide

1. **Navigate to Service Quotas**
   ```
   AWS Console → Service Quotas → AWS Services → Amazon Bedrock
   ```

2. **Filter for Claude Haiku 4.5**
   - Search for "Claude Haiku 4.5" or "Anthropic Claude Haiku"
   - Look for quotas with "Cross-region" in the name

3. **Request Increase**
   - Click on the quota name
   - Click "Request quota increase"
   - Enter your desired value
   - Provide a brief justification (optional but recommended):
     ```
     "Developing an AI agent application that makes multiple LLM calls per request. 
     Current 2 RPM limit is causing throttling during testing."
     ```

4. **Submit and Wait**
   - Most quota increases are **auto-approved** within **seconds to minutes**
   - Some may require manual review (24-48 hours)
   - You'll receive an email notification when approved

### Screenshot Reference

```
Service Quotas Console
├── AWS Services
│   └── Amazon Bedrock
│       ├── Cross-region model inference requests per minute for Anthropic Claude Haiku 4.5
│       │   Current: 2 → Request: 20 ✅
│       └── Global cross-region model inference requests per minute for Anthropic Claude Haiku 4.5
│           Current: 3 → Request: 50 ✅
```

---

## Understanding "Cross-Region" Inference

### What is Cross-Region Inference?

Cross-region inference allows you to invoke models across AWS regions for:
- **Higher availability**: If one region is down, requests route to another
- **Lower latency**: Route to the nearest region with capacity
- **Better throughput**: Distribute load across regions

### Model ID Format

When using cross-region inference, your model ID includes a region prefix:

```python
# Standard (single region)
LLM_MODEL = "anthropic.claude-3-5-haiku-20241022-v1:0"

# Cross-region (your current setup)
LLM_MODEL = "anthropic.claude-3-5-haiku-20241022:0"
```

### Implications

- You're using **cross-region quotas**, which are **separate** from single-region quotas
- Cross-region quotas are often **lower** by default
- But they provide **better reliability** for production workloads

---

## Recommended Quota Configuration

### For Development/Testing

```
Cross-region requests/min:     20 RPM
Global cross-region requests:  50 RPM
Tokens/min:                    500,000 (current)
```

**This allows:**
- ~3-4 schema generations per minute
- Comfortable margin for retries and errors
- Multiple developers testing simultaneously

### For Production

```
Cross-region requests/min:     100 RPM
Global cross-region requests:  200 RPM
Tokens/min:                    500,000 (current)
```

**This allows:**
- ~15-20 schema generations per minute
- ~1,000+ schemas per hour
- Headroom for traffic spikes

### For Heavy Production

```
Cross-region requests/min:     125 RPM (max available)
Global cross-region requests:  250 RPM (max available)
Tokens/min:                    500,000 (max available)
```

**This allows:**
- Maximum possible throughput
- ~20-25 schema generations per minute
- Best for high-traffic applications

---

## Monitoring Your Usage

### CloudWatch Metrics

Monitor your Bedrock usage in CloudWatch:

```
AWS Console → CloudWatch → Metrics → Bedrock
```

Key metrics:
- `ModelInvocations`: Number of model calls
- `InvocationThrottles`: Number of throttled requests
- `ModelInvocationLatency`: Response time
- `TokensUsed`: Token consumption

### Setting Up Alarms

Create alarms for throttling:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name bedrock-throttling \
  --alarm-description "Alert when Bedrock requests are throttled" \
  --metric-name InvocationThrottles \
  --namespace AWS/Bedrock \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1
```

---

## Cost Implications

### Claude Haiku 4.5 Pricing (as of 2024)

```
Input tokens:  $0.25 per 1M tokens
Output tokens: $1.25 per 1M tokens
```

### Estimated Costs

#### Per Schema Generation
- Input: ~2,000 tokens (prompts, context)
- Output: ~1,500 tokens (schema, reasoning)
- **Cost: ~$0.002 per schema** (0.2 cents)

#### Monthly Estimates

| Usage Level | Schemas/Day | Monthly Cost |
|-------------|-------------|--------------|
| Light testing | 100 | $6 |
| Development | 500 | $30 |
| Light production | 2,000 | $120 |
| Heavy production | 10,000 | $600 |

**Note:** These are estimates. Actual costs vary based on schema complexity.

---

## Troubleshooting Throttling

### If You're Still Getting Throttled After Quota Increases

1. **Check if quota increase was approved**
   ```bash
   aws service-quotas get-service-quota \
     --service-code bedrock \
     --quota-code <quota-code>
   ```

2. **Verify you're using the correct model ID**
   - Check your `.env` file
   - Ensure `provider="anthropic"` is set in LLM initialization

3. **Review your retry logic**
   - Current implementation: Exponential backoff up to 5 retries
   - Delays: 2s → 4s → 8s → 16s → 32s

4. **Add rate limiting to your application**
   ```python
   from langchain.callbacks import get_openai_callback
   
   # Track and limit your request rate
   ```

5. **Consider caching**
   ```python
   from langchain.cache import RedisCache
   
   # Cache LLM responses for repeated requests
   ```

---

## Summary & Next Steps

### ✅ Immediate Actions

1. **Request quota increase for "Cross-region requests/min" to 20-50 RPM**
2. **Request quota increase for "Global cross-region requests/min" to 50-100 RPM**
3. **Wait for approval** (usually < 1 hour)
4. **Re-run your tests**

### 📊 Monitor

1. Set up CloudWatch alarms for throttling
2. Track token usage and costs
3. Review LangSmith traces for performance insights

### 🚀 Optimize

1. Implement caching for repeated requests
2. Batch similar requests together
3. Use asynchronous processing for background tasks
4. Consider using a message queue (SQS) for request management

---

## Additional Resources

- [AWS Bedrock Quotas Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/quotas.html)
- [AWS Service Quotas User Guide](https://docs.aws.amazon.com/servicequotas/latest/userguide/intro.html)
- [Claude Pricing](https://www.anthropic.com/pricing)
- [Bedrock CloudWatch Metrics](https://docs.aws.amazon.com/bedrock/latest/userguide/monitoring-cw.html)

