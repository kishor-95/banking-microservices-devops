# Banking Microservices Infrastructure - Dev Environment

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Terraform** >= 1.6
3. **kubectl** for Kubernetes management
4. **EC2 key pair** created in ap-south-1 region

## Initial Setup

### 1. Create Backend Resources (One-Time)
```bash
# Create S3 bucket for state
aws s3api create-bucket \
  --bucket banking-terraform-state-ap-south-1 \
  --region ap-south-1 \
  --create-bucket-configuration LocationConstraint=ap-south-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket banking-terraform-state-ap-south-1 \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket banking-terraform-state-ap-south-1 \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# Create DynamoDB table for locking
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region ap-south-1
```

### 2. Configure Variables

Edit `terraform.tfvars`:
- Set `ec2_key_name` to your EC2 key pair name
- Set `allowed_ssh_cidr_blocks` to your IP address
- Review and adjust other variables as needed

### 3. Deploy Infrastructure
```bash
cd environments/dev

# Initialize Terraform
terraform init

# Review plan
terraform plan

# Apply (takes ~15-20 minutes)
terraform apply
```

## Post-Deployment

### 1. Configure kubectl
```bash
# SSH to bastion first
ssh -i /path/to/your-key.pem ec2-user@<BASTION_IP>

# Configure kubectl
aws eks update-kubeconfig --region ap-south-1 --name banking-eks-dev

# Verify connection
kubectl get nodes
```

### 2. Install AWS Load Balancer Controller
```bash
# Add Helm repo
helm repo add eks https://aws.github.io/eks-charts
helm repo update

# Get IAM role ARN from Terraform outputs
ROLE_ARN=$(terraform output -raw aws_load_balancer_controller_role_arn)

# Install controller
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=banking-eks-dev \
  --set serviceAccount.create=true \
  --set serviceAccount.name=aws-load-balancer-controller \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=$ROLE_ARN

# Verify
kubectl get deployment -n kube-system aws-load-balancer-controller
```

### 3. Access RDS
```bash
# Get RDS password from Secrets Manager
SECRET_ARN=$(terraform output -raw rds_master_user_secret_arn)
aws secretsmanager get-secret-value --secret-id $SECRET_ARN --query SecretString --output text

# Connect from bastion
RDS_ENDPOINT=$(terraform output -raw rds_endpoint)
psql -h $RDS_ENDPOINT -U dbadmin -d bankingdb
```

## Security Considerations

⚠️ **CRITICAL FOR PRODUCTION:**

1. **NAT Gateway**: Currently using single NAT for cost. For prod, set `single_nat_gateway = false`
2. **Instance Types**: t3.medium is for dev. Use c6i/c7i for prod banking workloads
3. **Deletion Protection**: RDS has deletion protection enabled. To destroy, set `db_deletion_protection = false`
4. **Bastion Access**: Restrict to specific IPs only
5. **EKS API**: Private endpoint only - access via bastion or VPN

## Cost Estimate (Monthly)

- VPC (NAT Gateway): ~$45
- EKS Cluster: ~$73
- EKS Nodes (2x t3.medium): ~$60
- RDS (db.t3.medium Multi-AZ): ~$120
- Bastion (t3.micro): ~$8
- **Total: ~$306/month**

## Cleanup
```bash
# WARNING: This destroys everything
terraform destroy

# If deletion protection is enabled on RDS, first disable it:
# Set db_deletion_protection = false in terraform.tfvars, then apply
```
