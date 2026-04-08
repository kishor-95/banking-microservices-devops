# Security Groups - Least privilege principle enforcement

# Bastion Security Group
resource "aws_security_group" "bastion" {
  name_prefix = "${var.name_prefix}-bastion"
  description = "Security group for bastion host - SSH access only"
  vpc_id      = var.vpc_id

  ingress {
    description = "SSH from authorized IP only"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidr_blocks
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  

  tags = merge(
    var.common_tags,
    {
      Name = "${var.name_prefix}-bastion-sg"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

# EKS Node Security Group (additional rules, EKS module creates primary SG)
resource "aws_security_group" "eks_additional" {
  name_prefix = "${var.name_prefix}-eks-additional-"
  description = "Additional security group for EKS nodes"
  vpc_id      = var.vpc_id

    egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${var.name_prefix}-eks-additional-sg"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

# Allow bastion to access EKS nodes for kubectl
resource "aws_security_group_rule" "eks_api_from_bastion" {
  description              = "Allow bastion to access EKS API"
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.bastion.id

  # 🔥 THIS IS THE IMPORTANT PART
  security_group_id = var.eks_cluster_security_group_id
}

# resource "aws_security_group_rule" "eks_from_bastion" {
#   type                     = "ingress"
#   from_port                = 443
#   to_port                  = 443
#   protocol                 = "tcp"
#   source_security_group_id = aws_security_group.bastion.id
#   security_group_id        = aws_security_group.eks_additional.id
#   description              = "Allow bastion to access EKS API"
# }

# RDS Security Group
resource "aws_security_group" "rds" {
  name_prefix = "${var.name_prefix}-rds-"
  description = "Security group for RDS - Allow access from EKS nodes only"
  vpc_id      = var.vpc_id

  tags = merge(
    var.common_tags,
    {
      Name = "${var.name_prefix}-rds-sg"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

# RDS ingress rule - dynamically created after EKS security group is available
resource "aws_security_group_rule" "rds_from_eks" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = var.eks_node_security_group_id
  security_group_id        = aws_security_group.rds.id
  description              = "PostgreSQL access from EKS nodes only"
}

# Allow RDS access from bastion for administrative tasks
resource "aws_security_group_rule" "rds_from_bastion" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.bastion.id
  security_group_id        = aws_security_group.rds.id
  description              = "PostgreSQL access from bastion for admin"
}