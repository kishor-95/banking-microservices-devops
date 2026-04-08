# Bastion Host - Gateway to private infrastructure
# Ubuntu


data "aws_ami" "ubuntu" {

    most_recent = true

    filter {
        name   = "name"
        values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
    }

    filter {
        name = "virtualization-type"
        values = ["hvm"]
    }

    owners = ["099720109477"]
}

output "test" {
  value = data.aws_ami.ubuntu
}


# Bastion Host EC2 Instance

resource "aws_instance" "bastion" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  key_name      = var.key_name
  iam_instance_profile = aws_iam_instance_profile.bastion.name

  subnet_id                   = var.subnet_id
  vpc_security_group_ids      = [var.security_group_id]
  associate_public_ip_address = true

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 20
    encrypted             = true
    delete_on_termination = true
  }

 user_data = <<-EOF
              #!/bin/bash
              set -e

              # Update system
              apt-get update -y
              apt-get upgrade -y

              # Install basic tools
              apt-get install -y \
                curl \
                unzip \
                ca-certificates \
                apt-transport-https \
                software-properties-common

              # Install AWS CLI v2
              curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
              unzip awscliv2.zip
              ./aws/install
             

              # Install kubectl
              curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
              install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

              # Install PostgreSQL client
              apt-get install -y postgresql-client

              # Install SSM Agent (Ubuntu way)
              snap install amazon-ssm-agent --classic
              systemctl enable snap.amazon-ssm-agent.amazon-ssm-agent.service
              systemctl start snap.amazon-ssm-agent.amazon-ssm-agent.service

              EOF

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"  # IMDSv2 required for security
    http_put_response_hop_limit = 1
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${var.name_prefix}-bastion"
    }
  )
}

# Elastic IP for bastion
resource "aws_eip" "bastion" {
  count    = var.create_eip ? 1 : 0
  instance = aws_instance.bastion.id
  domain   = "vpc"

  tags = merge(
    var.common_tags,
    {
      Name = "${var.name_prefix}-bastion-eip"
    }
  )
}

resource "aws_iam_role" "bastion" {
  name = "${var.name_prefix}-bastion-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "bastion_eks" {
  role       = aws_iam_role.bastion.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

resource "aws_iam_instance_profile" "bastion" {
  name = "${var.name_prefix}-bastion-profile"
  role = aws_iam_role.bastion.name
}