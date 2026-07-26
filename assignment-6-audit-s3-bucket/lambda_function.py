import logging
import os
import boto3
from botocore.exceptions import ClientError

# Initialize structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Boto3 clients
s3_client = boto3.client("s3")
sns_client = boto3.client("sns")

# Environment variables
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN")

def check_block_public_access(bucket_name):
    """Checks if Block Public Access (BPA) is completely enabled on the bucket."""
    try:
        response = s3_client.get_public_access_block(Bucket=bucket_name)
        config = response.get("PublicAccessBlockConfiguration", {})
        # If any of the 4 block settings are False, it's considered unblocked/vulnerable
        is_blocked = all([
            config.get("BlockPublicAcls", False),
            config.get("IgnorePublicAcls", False),
            config.get("BlockPublicPolicy", False),
            config.get("RestrictPublicBuckets", False)
        ])
        return is_blocked, config
    except ClientError as e:
        # NoSuchPublicAccessBlockConfiguration means BPA is completely disabled
        if e.response['Error']['Code'] == 'NoSuchPublicAccessBlockConfiguration':
            return False, "No Public Access Block Configuration set."
        logger.warning(f"Error reading PublicAccessBlock for {bucket_name}: {str(e)}")
        return False, str(e)

def check_bucket_policy_status(bucket_name):
    """Checks if the bucket policy is explicitly marked as public."""
    try:
        response = s3_client.get_bucket_policy_status(Bucket=bucket_name)
        return response.get("PolicyStatus", {}).get("IsPublic", False)
    except ClientError as e:
        # NoSuchBucketPolicy means no policy exists, so policy isn't public
        if e.response['Error']['Code'] == 'NoSuchBucketPolicy':
            return False
        logger.warning(f"Error checking policy status for {bucket_name}: {str(e)}")
        return False

def check_bucket_acls(bucket_name):
    """Checks if ACLs grant public READ or WRITE permissions."""
    public_uri = "http://acs.amazonaws.com/groups/global/AllUsers"
    try:
        response = s3_client.get_bucket_acl(Bucket=bucket_name)
        for grant in response.get("Grants", []):
            grantee = grant.get("Grantee", {})
            if grantee.get("URI") == public_uri:
                return True
        return False
    except ClientError as e:
        logger.warning(f"Error reading ACL for {bucket_name}: {str(e)}")
        return False

def lambda_handler(event, context):
    """
    Audits all S3 buckets in the account for public access via:
    1. Block Public Access settings
    2. Bucket Policy Status
    3. ACL Grants
    """
    logger.info("Starting security audit for public S3 buckets...")
    
    try:
        buckets_response = s3_client.list_buckets()
        buckets = buckets_response.get("Buckets", [])
        logger.info(f"Discovered {len(buckets)} total buckets to audit.")

        public_buckets = []

        for b in buckets:
            b_name = b["Name"]
            logger.info(f"Auditing bucket: '{b_name}'...")

            bpa_enabled, bpa_details = check_block_public_access(b_name)
            policy_is_public = check_bucket_policy_status(b_name)
            acl_is_public = check_bucket_acls(b_name)

            # Determine public status
            is_public = (not bpa_enabled) or policy_is_public or acl_is_public

            if is_public:
                findings = []
                if not bpa_enabled:
                    findings.append("Block Public Access is DISABLED or INCOMPLETE")
                if policy_is_public:
                    findings.append("Bucket Policy is PUBLIC")
                if acl_is_public:
                    findings.append("ACL Grants PUBLIC access")

                public_buckets.append({
                    "bucket_name": b_name,
                    "reasons": findings
                })
                logger.warning(f"SECURITY ALERT: Bucket '{b_name}' is PUBLIC! Reasons: {findings}")

        if public_buckets:
            # Build SNS alert payload
            message_lines = [
                "🚨 AWS Security Alert: Public S3 Buckets Detected!",
                f"\nThe audit found {len(public_buckets)} publicly exposed bucket(s):\n"
            ]
            
            for pb in public_buckets:
                message_lines.append(f"• Bucket Name: {pb['bucket_name']}")
                for r in pb['reasons']:
                    message_lines.append(f"   - Finding: {r}")
                message_lines.append("")

            message_lines.append("Action Required: Please re-enable 'Block Public Access' and review policies immediately.")
            
            full_message = "\n".join(message_lines)
            
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject=f"🚨 Security Alert: {len(public_buckets)} Public S3 Bucket(s) Detected",
                Message=full_message
            )
            
            return {
                "statusCode": 200,
                "body": f"Audit complete. Alert sent for {len(public_buckets)} public bucket(s)."
            }

        else:
            logger.info("Security Audit Complete: All S3 buckets are properly secured.")
            return {
                "statusCode": 200,
                "body": "All buckets are secure. No public access detected."
            }

    except Exception as e:
        logger.error(f"Error performing S3 public access audit: {str(e)}")
        raise e