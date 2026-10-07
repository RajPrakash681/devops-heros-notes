output "vpc_id" {
  description = "ID of the VPC."
  value       = aws_vpc.main.id
}

output "public_subnet_id" {
  description = "ID of the public subnet."
  value       = aws_subnet.public.id
}

output "public_subnet_az" {
  description = "Availability Zone the subnet (and so the instance) is in."
  value       = aws_subnet.public.availability_zone
}

output "security_group_id" {
  description = "ID of the web security group."
  value       = aws_security_group.web.id
}

output "ami" {
  description = "AMI the data source picked."
  value       = "${data.aws_ami.al2023.id} (${data.aws_ami.al2023.name})"
}

output "instance_id" {
  description = "ID of the EC2 instance."
  value       = aws_instance.web.id
}

output "instance_public_ip" {
  description = "Public IP of the EC2 instance."
  value       = aws_instance.web.public_ip
}

output "web_url" {
  description = "Where nginx would answer on real AWS."
  value       = "http://${aws_instance.web.public_ip}"
}

output "bucket_name" {
  description = "Name of the assets bucket."
  value       = aws_s3_bucket.assets.bucket
}
