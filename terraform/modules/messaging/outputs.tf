output "sns_topic_arn" {
  value = aws_sns_topic.order_processing.arn
}

output "sqs_queue_url" {
  value = aws_sqs_queue.order_processing.url
}