# SNS Topic
resource "aws_sns_topic" "order_processing" {
  name = "order-processing-events"
}

# SQS Queue
resource "aws_sqs_queue" "order_processing" {
  name                      = "order-processing-queue"
  message_retention_seconds = 345600  # 4 days
  visibility_timeout_seconds = 30
  receive_wait_time_seconds = 20      # Long polling
}

# Subscribe SQS to SNS
resource "aws_sns_topic_subscription" "sqs_subscription" {
  topic_arn = aws_sns_topic.order_processing.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.order_processing.arn
}

# Allow SNS to send messages to SQS
resource "aws_sqs_queue_policy" "order_processing_policy" {
  queue_url = aws_sqs_queue.order_processing.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "sns.amazonaws.com"
      }
      Action   = "sqs:SendMessage"
      Resource = aws_sqs_queue.order_processing.arn
      Condition = {
        ArnEquals = {
          "aws:SourceArn" = aws_sns_topic.order_processing.arn
        }
      }
    }]
  })
}