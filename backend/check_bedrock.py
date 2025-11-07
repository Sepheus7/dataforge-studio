"""
Diagnostic script to check AWS Bedrock configuration and available models
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Load .env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

def check_credentials():
    """Check if AWS credentials are configured"""
    print("1️⃣  Checking AWS Credentials...")
    print("-" * 60)
    
    region = os.getenv('AWS_REGION', 'us-east-1')
    access_key = os.getenv('AWS_ACCESS_KEY_ID')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    print(f"   AWS_REGION: {region}")
    print(f"   AWS_ACCESS_KEY_ID: {'✅ Set' if access_key else '❌ NOT SET'}")
    print(f"   AWS_SECRET_ACCESS_KEY: {'✅ Set' if secret_key else '❌ NOT SET'}")
    
    if not access_key or not secret_key:
        print("\n❌ AWS credentials not configured!")
        print("   Add AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY to your .env file")
        return False, region
    
    return True, region


def check_bedrock_access(region):
    """Check if Bedrock API is accessible"""
    print("\n\n2️⃣  Checking Bedrock API Access...")
    print("-" * 60)
    
    try:
        bedrock = boto3.client('bedrock', region_name=region)
        print(f"   ✅ Successfully connected to Bedrock in {region}")
        return True, bedrock
    except NoCredentialsError:
        print("   ❌ No valid AWS credentials found")
        return False, None
    except ClientError as e:
        print(f"   ❌ Error connecting to Bedrock: {e}")
        return False, None


def list_available_models(bedrock):
    """List all available foundation models"""
    print("\n\n3️⃣  Checking Available Models...")
    print("-" * 60)
    
    try:
        response = bedrock.list_foundation_models()
        models = response.get('modelSummaries', [])
        
        # Filter for Claude models
        claude_models = [m for m in models if 'claude' in m.get('modelId', '').lower()]
        
        if not claude_models:
            print("   ⚠️  No Claude models found!")
            print("   This might mean:")
            print("      - Model access not enabled in AWS Console")
            print("      - Models not available in your region")
            return []
        
        print(f"   Found {len(claude_models)} Claude models:\n")
        
        for model in claude_models:
            model_id = model.get('modelId')
            model_name = model.get('modelName')
            status = model.get('modelLifecycle', {}).get('status', 'UNKNOWN')
            
            if 'haiku' in model_id.lower():
                print(f"   🎯 {model_id}")
                print(f"      Name: {model_name}")
                print(f"      Status: {status}")
                print()
        
        return claude_models
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'AccessDeniedException':
            print("   ❌ Access Denied!")
            print("   Your IAM user needs Bedrock permissions")
            print("   Required: bedrock:ListFoundationModels")
        else:
            print(f"   ❌ Error: {e}")
        return []


def check_model_access(bedrock, model_id):
    """Check if a specific model can be invoked"""
    print(f"\n\n4️⃣  Testing Model Access: {model_id}")
    print("-" * 60)
    
    try:
        bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        
        # Try a minimal test invocation
        test_payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 10,
            "messages": [
                {"role": "user", "content": "Hi"}
            ]
        }
        
        import json
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(test_payload)
        )
        
        print(f"   ✅ Model '{model_id}' is accessible and working!")
        return True
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        
        if error_code == 'AccessDeniedException':
            print(f"   ❌ Access Denied to model!")
            print(f"   Error: {error_msg}")
            print("\n   📋 TO FIX:")
            print("   1. Go to AWS Console → Bedrock → Model access")
            print("   2. Click 'Manage model access'")
            print("   3. Enable 'Claude 3.5 Haiku'")
            print("   4. Save changes and wait for approval (usually instant)")
        elif error_code == 'ValidationException':
            print(f"   ❌ Model ID invalid or not available")
            print(f"   Error: {error_msg}")
            print("\n   This usually means:")
            print("   - Model not available in your region")
            print("   - Model ID format is incorrect")
        else:
            print(f"   ❌ Error: {error_code} - {error_msg}")
        
        return False


def main():
    print("=" * 60)
    print("  AWS BEDROCK DIAGNOSTIC CHECK")
    print("=" * 60)
    
    # Check credentials
    has_creds, region = check_credentials()
    if not has_creds:
        sys.exit(1)
    
    # Check Bedrock access
    has_access, bedrock = check_bedrock_access(region)
    if not has_access:
        sys.exit(1)
    
    # List available models
    models = list_available_models(bedrock)
    
    # Check specific model
    target_model = os.getenv('LLM_MODEL', 'anthropic.claude-3-5-haiku-20241022:0')
    check_model_access(bedrock, target_model)
    
    print("\n\n" + "=" * 60)
    print("  DIAGNOSTIC COMPLETE")
    print("=" * 60)
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    print("-" * 60)
    print("If model access is denied:")
    print("1. AWS Console: https://console.aws.amazon.com/bedrock/")
    print("2. Click 'Model access' in left sidebar")
    print("3. Click 'Manage model access'")
    print("4. Find 'Claude 3.5 Haiku' and enable it")
    print("5. Click 'Save changes'")
    print("6. Wait a few minutes, then re-run this script")
    print("\nClaude Haiku 4.5 is available in these regions:")
    print("  • us-east-1 (N. Virginia)")
    print("  • us-west-2 (Oregon)")
    print("  • eu-central-1 (Frankfurt)")
    print("  • ap-southeast-2 (Sydney)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

