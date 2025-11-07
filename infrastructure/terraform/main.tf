terraform {
  required_version = ">= 1.5"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.20"
    }
  }
  
  # Backend configuration for state storage
  backend "s3" {
    bucket         = "dataforge-terraform-state"
    key            = "dataforge-studio/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "dataforge-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "DataForge Studio"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Data source for availability zones
data "aws_availability_zones" "available" {
  state = "available"
}

# KMS key for encryption
resource "aws_kms_key" "dataforge" {
  description             = "DataForge Studio encryption key"
  deletion_window_in_days = 10
  enable_key_rotation     = true
  
  tags = {
    Name = "dataforge-${var.environment}"
  }
}

resource "aws_kms_alias" "dataforge" {
  name          = "alias/dataforge-${var.environment}"
  target_key_id = aws_kms_key.dataforge.key_id
}

