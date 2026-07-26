from datetime import datetime, timezone
import logging
import boto3

# Setup structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS SDK clients
ec2_client = boto3.client("ec2")
cloudtrail_client = boto3.client("cloudtrail")

def get_launching_user(instance_id):
    """
    BONUS FEATURE: Queries CloudTrail to find the IAM User or Role 
    that executed the 'RunInstances' API call for this instance.
    """
    try:
        response = cloudtrail_client.lookup_events(
            LookupAttributes=[
                {
                    "AttributeKey": "ResourceName",
                    "AttributeValue": instance_id
                }
            ],
            MaxResults=5
        )
        for event in response.get("Events", []):
            if event.get("EventName") == "RunInstances":
                username = event.get("Username", "Unknown")
                logger.info(f"CloudTrail lookup success: Instance {instance_id} launched by '{username}'")
                return username
    except Exception as e:
        logger.warning(f"Could not retrieve launching user from CloudTrail: {str(e)}")
    
    return "AutoProvisioned"

def lambda_handler(event, context):
    """
    Triggered by EventBridge EC2 State-change Notification (state: running).
    Automatically applies governance and resource-tracking tags.
    """
    logger.info(f"Event received: {event}")
    
    # Extract Instance ID from EventBridge payload
    detail = event.get("detail", {})
    instance_id = detail.get("instance-id")

    if not instance_id:
        logger.error("No instance-id found in EventBridge event payload.")
        return {"statusCode": 400, "body": "Missing instance-id parameter."}

    # Generate current UTC date string
    launch_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Fetch launching IAM user (Bonus feature)
    owner = get_launching_user(instance_id)

    logger.info(f"Applying operational tags to EC2 Instance: {instance_id}")

    try:
        # Tag the instance
        ec2_client.create_tags(
            Resources=[instance_id],
            Tags=[
                {"Key": "LaunchDate", "Value": launch_date},
                {"Key": "Environment", "Value": "Dev"},
                {"Key": "ManagedBy", "Value": "LambdaAutoTagger"},
                {"Key": "Owner", "Value": owner}
            ]
        )
        
        confirmation_msg = f"Successfully tagged instance {instance_id} with LaunchDate={launch_date}, Environment=Dev, Owner={owner}"
        logger.info(confirmation_msg)

        return {
            "statusCode": 200,
            "body": confirmation_msg
        }

    except Exception as e:
        logger.error(f"Error applying tags to instance {instance_id}: {str(e)}")
        raise e