resource "aws_dynamodb_table" "users" {
    name = "UsersTable"
    billing_mode = "PROVISIONED"
    read_capacity = 100
    write_capacity = 50

    hash_key = "userId"
    
    attribute {
        name = "userId"
        type = "N"  # String data type
    }

    tags = {
        Name = "UsersTable"
    }

}

resource "aws_dynamodb_table" "reservations" {
    name = "ReservationsTable"
    billing_mode = "PAY_PER_REQUEST"
    #read_capacity = 100
    #write_capacity = 50

    hash_key = "bookingId"
    range_key = "date"
    
    attribute {
        name = "bookingId"
        type = "N"  # String data type
    }

     attribute {
        name = "date"
        type = "S"  # String data type
    }

    replica {
        region_name = "us-west-2"
    }

    global_secondary_index {
        name            = "DateIndex"
        hash_key        = "date"     
        range_key       = "bookingId"      
        projection_type = "ALL"
        write_capacity  = 50
        read_capacity   = 50
    }

    tags = {
        Name = "ReservationsTable"
    }

}

resource "aws_dynamodb_table" "spaces" {
    name = "SpacesTable"
    billing_mode = "PROVISIONED"
    read_capacity = 100
    write_capacity = 50

    hash_key = "spaceID"
    
    attribute {
        name = "spaceID"
        type = "S"  # String data type
    }

    tags = {
        Name = "SpacesTable"
    }

}

resource "aws_route53_record" "dynamodb_endpoint_us_east_1" {
  zone_id = aws_route53_zone.main_zone.zone_id
  name    = "dynamodb.robin.com"
  type    = "A" # or ALIAS if using an AWS resource
  ttl     = 300
  records = ["${aws_dynamodb_table.main_table.arn}.dynamodb.amazonaws.com"] # This is a placeholder, actual endpoint might differ
  set_identifier = "us-east-1"
  latency_routing_policy {
    region = "us-east-1"
  }
}

resource "aws_route53_record" "dynamodb_endpoint_us_west_2" {
  zone_id = aws_route53_zone.main_zone.zone_id
  name    = "dynamodb.robin.com"
  type    = "A"
  ttl     = 300
  records = ["${aws_dynamodb_table_replica.replica_us_west_2.arn}.dynamodb.amazonaws.com"] # Placeholder
  set_identifier = "us-west-2"
  latency_routing_policy {
    region = "us-west-2"
  }
}