# Latest Amazon Linux 2023 (x86_64) published by Amazon, looked up at plan time instead
# of a hard-coded AMI ID (AMI IDs differ per region and go stale).
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

resource "aws_instance" "web" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.web.id]

  # Runs once at first boot. It needs the internet (dnf downloads nginx).
  # Deliberately does not interpolate var.instance_name: any change to user_data makes the
  # provider stop and start the instance, so renaming it would have meant a reboot.
  user_data = <<-EOT
    #!/bin/bash
    dnf install -y nginx
    echo "Hello from ${var.project_name} - built by Terraform" > /usr/share/nginx/html/index.html
    systemctl enable --now nginx
  EOT

  tags = {
    Name = var.instance_name
  }

  # Explicit dependency. The references above already make Terraform create the subnet
  # and security group first - but nothing here refers to the route table, so Terraform
  # would happily launch the instance in parallel with the 0.0.0.0/0 route being
  # attached to the subnet. The user_data above needs that route at first boot to
  # download nginx, so the instance must wait for the association. Terraform cannot
  # infer that from the code; depends_on states it.
  depends_on = [aws_route_table_association.public]
}
