import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ec2_client = boto3.client("ec2")

def lambda_handler(event, context):
    action = event.get("action", "").upper()
    logger.info(f"Triggered execution with action: {action}")
    
    if action not in ["START", "STOP"]:
        logger.error(f"Invalid action: '{action}'. Expected 'START' or 'STOP'.")
        return {"statusCode": 400, "body": "Invalid action parameter."}

    try:
        response = ec2_client.describe_instances(
            Filters=[
                {"Name": "tag:Environment", "Values": ["Dev"]},
                {"Name": "instance-state-name", "Values": ["running", "stopped"]}
            ]
        )
        
        instance_ids = [
            inst["InstanceId"]
            for res in response.get("Reservations", [])
            for inst in res.get("Instances", [])
        ]

        if not instance_ids:
            logger.info("No EC2 instances found matching tag 'Environment=Dev'.")
            return {"statusCode": 200, "body": "No target instances found."}

        logger.info(f"Target Instance IDs: {instance_ids}")

        if action == "START":
            ec2_client.start_instances(InstanceIds=instance_ids)
            logger.info(f"Initiated START for: {instance_ids}")
            return {"statusCode": 200, "body": f"Started instances: {instance_ids}"}

        elif action == "STOP":
            ec2_client.stop_instances(InstanceIds=instance_ids)
            logger.info(f"Initiated STOP for: {instance_ids}")
            return {"statusCode": 200, "body": f"Stopped instances: {instance_ids}"}

    except Exception as e:
        logger.error(f"Error during EC2 automation: {str(e)}")
        raise e
