locals {
  common_tags = {
    project     = var.project_name
    environment = var.environment
    managed_by  = "terraform"
  }
}

provider "aws" {
  alias  = "primary"
  region = var.regions[0]
}

provider "aws" {
  alias  = "secondary"
  region = var.regions[1]
}

provider "aws" {
  alias  = "tertiary"
  region = var.regions[2]
}

resource "aws_s3_bucket" "artifacts_primary" {
  provider = aws.primary
  bucket   = "${var.project_name}-${var.environment}-artifacts-primary"
  tags     = local.common_tags
}

resource "aws_s3_bucket_versioning" "artifacts_primary" {
  bucket = aws_s3_bucket.artifacts_primary.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_kinesis_stream" "events_primary" {
  provider         = aws.primary
  name             = "${var.project_name}-${var.environment}-events-primary"
  shard_count      = 4
  retention_period = 48
  tags             = local.common_tags
}

resource "aws_eks_cluster" "control_primary" {
  provider = aws.primary
  name     = "${var.project_name}-${var.environment}-primary"
  role_arn = "arn:aws:iam::123456789012:role/replace-me-eks-cluster-role"
  version  = "1.31"

  vpc_config {
    subnet_ids = ["subnet-replace-a", "subnet-replace-b", "subnet-replace-c"]
  }

  tags = local.common_tags
}

