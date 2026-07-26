from datetime import datetime, timezone
import logging
import os
import time
import boto3

# Initialize structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Boto3 EC2 client
ec2_client = boto3.client("ec2")

# Environment variables
TARGET_VOLUME_ID = os.environ.get("TARGET_VOLUME_ID", "vol-0123456789abcdef0")
INSTANCE_TYPE = os.environ.get("INSTANCE_TYPE", "t3.micro")

def lambda_handler(event, context):
    """
    Automated Disaster Recovery:
    1. Identifies the latest snapshot for a given volume ID.
    2. Registers a new AMI from the snapshot.
    3. Launches a new EC2 instance from the AMI.
    4. Tags the new instance for operational tracking.
    """
    logger.info(f"Initiating Disaster Recovery restore procedure for Volume ID: {TARGET_VOLUME_ID}")

    try:
        # Step 1: Find the most recent snapshot for the volume
        response = ec2_client.describe_snapshots(
            OwnerIds=["self"],
            Filters=[
                {"Name": "volume-id", "Values": [TARGET_VOLUME_ID]}
            ]
        )
        snapshots = response.get("Snapshots", [])

        if not snapshots:
            err_msg = f"No snapshots found for Volume ID: {TARGET_VOLUME_ID}"
            logger.error(err_msg)
            return {"statusCode": 404, "body": err_msg}

        # Sort snapshots by StartTime descending to get the latest
        latest_snapshot = sorted(snapshots, key=lambda x: x["StartTime"], reverse=True)[0]
        snapshot_id = latest_snapshot["SnapshotId"]
        snapshot_time = latest_snapshot["StartTime"]
        logger.info(f"Identified latest snapshot: {snapshot_id} (Created at: {snapshot_time})")

        # Step 2: Register a custom AMI from the snapshot
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        ami_name = f"restored-ami-{snapshot_id}-{timestamp_str}"
        
        logger.info(f"Registering AMI '{ami_name}' from Snapshot {snapshot_id}...")
        ami_response = ec2_client.register_image(
            Name=ami_name,
            Description=f"Disaster Recovery AMI built from snapshot {snapshot_id}",
            Architecture="x86_64",
            RootDeviceName="/dev/xvda",
            BlockDeviceMappings=[
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "SnapshotId": snapshot_id,
                        "VolumeSize": latest_snapshot.get("VolumeSize", 8),
                        "VolumeType": "gp3",
                        "DeleteOnTermination": True
                    }
                }
            ],
            VirtualizationType="hvm",
            EnaSupport=True
        )
        
        ami_id = ami_response["ImageId"]
        logger.info(f"Successfully registered AMI: {ami_id}")

        # Step 3: Wait until AMI becomes available before launching instance
        logger.info(f"Waiting for AMI {ami_id} to become available...")
        waiter = ec2_client.get_waiter("image_available")
        waiter.wait(ImageIds=[ami_id], WaiterConfig={"Delay": 15, "MaxAttempts": 20})
        logger.info(f"AMI {ami_id} is now AVAILABLE.")

        # Step 4: Launch a new EC2 instance from the AMI
        logger.info(f"Launching new {INSTANCE_TYPE} instance from AMI {ami_id}...")
        run_response = ec2_client.run_instances(
            ImageId=ami_id,
            InstanceType=INSTANCE_TYPE,
            MinCount=1,
            MaxCount=1,
            TagSpecifications=[
                {
                    "ResourceType": "instance",
                    "Tags": [
                        {"Key": "Name", "Value": "Restored-DR-Instance"},
                        {"Key": "RestoredFrom", "Value": snapshot_id},
                        {"Key": "RestoredAMI", "Value": ami_id},
                        {"Key": "Environment", "Value": "DisasterRecovery"},
                        {"Key": "ManagedBy", "Value": "LambdaDRRestore"}
                    ]
                }
            ]
        )

        new_instance_id = run_response["Instances"][0]["InstanceId"]
        logger.info(f"Successfully launched restored EC2 Instance ID: {new_instance_id}")

        return {
            "statusCode": 200,
            "body": {
                "message": "EC2 Disaster Recovery Restore Completed Successfully.",
                "latest_snapshot_id": snapshot_id,
                "registered_ami_id": ami_id,
                "restored_instance_id": new_instance_id
            }
        }

    except Exception as e:
        logger.error(f"Error during instance restore workflow: {str(e)}")
        raise e