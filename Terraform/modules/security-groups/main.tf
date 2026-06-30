# =============================================================================
# SECURITY GROUPS MODULE - Least Privilege Access Control
# =============================================================================
# Creates security groups for:
# - ALB (Application Load Balancer) - ingress on 80, 443
# - EKS Nodes - managed by EKS module, additional rules here
# - RDS - ingress from EKS nodes and ALB on port 5432
# =============================================================================

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      # version = "=> 6.42.0"
    }
  }
}

# =============================================================================
# ALB SECURITY GROUP
# =============================================================================
resource "aws_security_group" "alb" {
  name_prefix = "${var.name_prefix}-alb-"
  description = "Security group for Application Load Balancer - HTTP/HTTPS only"
  vpc_id      = var.vpc_id

  tags = merge(
    var.common_tags,
    {
      Name = "${var.name_prefix}-alb-sg"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

# ALB ingress - HTTP
resource "aws_security_group_rule" "alb_ingress_http" {
  type              = "ingress"
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.alb.id
  description       = "HTTP from internet"
}

# ALB ingress - HTTPS
resource "aws_security_group_rule" "alb_ingress_https" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.alb.id
  description       = "HTTPS from internet"
}

# ALB egress - all outbound traffic
resource "aws_security_group_rule" "alb_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.alb.id
  description       = "Allow all outbound traffic"
}

# =============================================================================
# EKS NODES ADDITIONAL SECURITY GROUP
# =============================================================================
# EKS module creates primary SG; this allows additional rules
resource "aws_security_group" "eks_additional" {
  name_prefix = "${var.name_prefix}-eks-additional-"
  description = "Additional security group for EKS nodes"
  vpc_id      = var.vpc_id

  tags = merge(
    var.common_tags,
    {
      Name                                       = "${var.name_prefix}-eks-additional-sg"
      "kubernetes.io/cluster/${var.cluster_name}" = "owned"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

# Allow EKS nodes to receive traffic from ALB
resource "aws_security_group_rule" "eks_from_alb_http" {
  type                     = "ingress"
  from_port                = 80
  to_port                  = 80
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.alb.id
  security_group_id        = aws_security_group.eks_additional.id
  description              = "HTTP traffic from ALB to EKS nodes"
}

resource "aws_security_group_rule" "eks_from_alb_https" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.alb.id
  security_group_id        = aws_security_group.eks_additional.id
  description              = "HTTPS traffic from ALB to EKS nodes"
}

# Allow EKS nodes to communicate with each other
resource "aws_security_group_rule" "eks_node_to_node" {
  type                     = "ingress"
  from_port                = 0
  to_port                  = 65535
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.eks_additional.id
  security_group_id        = aws_security_group.eks_additional.id
  description              = "Node-to-node communication"
}

# EKS nodes need outbound internet access (pulled images, APIs, etc.)
resource "aws_security_group_rule" "eks_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.eks_additional.id
  description       = "Allow all outbound traffic for updates, downloads, external APIs"
}

# =============================================================================
# RDS SECURITY GROUP
# =============================================================================
resource "aws_security_group" "rds" {
  name_prefix = "${var.name_prefix}-rds-"
  description = "Security group for RDS database - PostgreSQL from EKS only"
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

# RDS ingress - PostgreSQL from EKS nodes
resource "aws_security_group_rule" "rds_from_eks_nodes" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = var.eks_node_security_group_id
  security_group_id        = aws_security_group.rds.id
  description              = "PostgreSQL (5432) from EKS nodes"
}

# RDS ingress - PostgreSQL from ALB (for health checks if needed)
resource "aws_security_group_rule" "rds_from_alb" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.alb.id
  security_group_id        = aws_security_group.rds.id
  description              = "PostgreSQL (5432) from ALB"
}

# RDS egress - allow responses
resource "aws_security_group_rule" "rds_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.rds.id
  description       = "Allow all outbound traffic"
}
