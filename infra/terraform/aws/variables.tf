variable "regions" {
  description = "AWS regions for active-active deployment"
  type        = list(string)
  default     = ["us-east-1", "us-west-2", "eu-west-1"]
}

variable "project_name" {
  description = "Project name prefix"
  type        = string
  default     = "aegisworld"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

