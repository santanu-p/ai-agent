output "primary_eks_cluster_name" {
  value = aws_eks_cluster.control_primary.name
}

output "primary_artifacts_bucket" {
  value = aws_s3_bucket.artifacts_primary.bucket
}

output "primary_events_stream_name" {
  value = aws_kinesis_stream.events_primary.name
}

