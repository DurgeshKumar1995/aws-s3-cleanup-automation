from datetime import datetime, timezone, timedelta
import logging
import os
import boto3

# Setup structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Boto3 EC2 client
ec2_client = boto3.client("ec2")

# Environment variables
VOLUME_ID = os.environ.get("VOLUME_ID", "vol-0123456789abcdef0")
RETENTION_DAYS = int(os.environ.get("RETENTION_DAYS", "30"))
TAG_KEY = "CreatedBy"
TAG_VALUE = "Lambda-Backup"

def lambda_handler(event, context):
    """
    Creates a new snapshot of a specified EBS volume, tags it, 
    and deletes snapshots owned by self with the target tag older than RETENTION_DAYS.
    """
    now = datetime.now(timezone.utc)
    cutoff_time = now - timedelta(days=RETENTION_DAYS)

    logger.info(f"Starting EBS Backup and Cleanup for Volume: {VOLUME_ID}")
    
    # -------------------------------------------------------------
    # 1. CREATE NEW EBS SNAPSHOT
    # -------------------------------------------------------------
    try:
        snap_description = f"Automated Lambda Backup for {VOLUME_ID} on {now.strftime('%Y-%m-%d %H:%M:%S')}"
        new_snapshot = ec2_client.create_snapshot(
            VolumeId=VOLUME_ID,
            Description=snap_description,
            TagSpecifications=[
                {
                    "ResourceType": "snapshot",
                    "Tags": [
                        {"Key": TAG_KEY, "Value": TAG_VALUE},
                        {"Key": "Environment", "Value": "Dev"}
                    ]
                }
            ]
        )
        new_snap_id = new_snapshot["SnapshotId"]
        logger.info(f"Successfully created new snapshot: {new_snap_id}")

    except Exception as e:
        logger.error(f"Failed to create EBS Snapshot: {str(e)}")
        raise e

    # -------------------------------------------------------------
    # 2. PURGE STALE SNAPSHOTS (> 30 Days)
    # -------------------------------------------------------------
    deleted_snapshots = []
    try:
        # Fetch snapshots owned by 'self' with the target tag
        response = ec2_client.describe_snapshots(
            OwnerIds=["self"],
            Filters=[
                {"Name": f"tag:{TAG_KEY}", "Values": [TAG_VALUE]},
                {"Name": "volume-id", "Values": [VOLUME_ID]}
            ]
        )

        snapshots = response.get("Snapshots", [])
        logger.info(f"Found {len(snapshots)} total snapshot(s) managed by Lambda for volume {VOLUME_ID}.")

        for snap in snapshots:
            snap_id = snap["SnapshotId"]
            start_time = snap["StartTime"]  # UTC timezone-aware datetime

            # Don't evaluate the newly created snapshot
            if snap_id == new_snap_id:
                continue

            if start_time < cutoff_time:
                logger.info(f"Stale snapshot detected: {snap_id} (Created: {start_time}). Deleting...")
                ec2_client.delete_snapshot(SnapshotId=snap_id)
                deleted_snapshots.append(snap_id)
                logger.info(f"Successfully deleted snapshot: {snap_id}")

        logger.info(f"Execution Summary: Created Snapshot={new_snap_id} | Deleted Snapshots={deleted_snapshots}")

        return {
            "statusCode": 200,
            "body": {
                "message": "EBS Backup and Cleanup Completed Successfully.",
                "created_snapshot": new_snap_id,
                "deleted_snapshots": deleted_snapshots
            }
        }

    except Exception as e:
        logger.error(f"Error during snapshot cleanup phase: {str(e)}")
        raise e