from datetime import datetime, timezone
import logging
import os
import boto3

# Setup structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Boto3 clients
ce_client = boto3.client("ce")
sns_client = boto3.client("sns")

# Read configurations from environment variables
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN")
COST_THRESHOLD = float(os.environ.get("COST_THRESHOLD", "50.00"))

def lambda_handler(event, context):
    """
    Queries AWS Cost Explorer for Month-to-Date (MTD) UnblendedCost,
    compares it against COST_THRESHOLD, and publishes an SNS notification if exceeded.
    """
    now = datetime.now(timezone.utc)
    # Start of current month (YYYY-MM-01)
    start_date = now.strftime("%Y-%m-01")
    # Current date (YYYY-MM-DD)
    end_date = now.strftime("%Y-%m-%d")

    # If today is the 1st of the month, set end_date to tomorrow to satisfy Cost Explorer's requirement (End > Start)
    if start_date == end_date:
        end_date = (now.replace(day=2)).strftime("%Y-%m-%d")

    logger.info(f"Querying Cost Explorer MTD spend from {start_date} to {end_date}")

    try:
        # Query Month-to-Date spend
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                "Start": start_date,
                "End": end_date
            },
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"]
        )

        # Extract numerical amount and currency unit
        results = response.get("ResultsByTime", [])
        if not results:
            logger.warning("No cost data returned from Cost Explorer.")
            return {"statusCode": 200, "body": "No cost data available."}

        cost_amount_str = results[0]["Total"]["UnblendedCost"]["Amount"]
        currency = results[0]["Total"]["UnblendedCost"]["Unit"]
        current_spend = float(cost_amount_str)

        logger.info(f"Retrieved MTD Spend: {current_spend:.4f} {currency} (Threshold: ${COST_THRESHOLD:.2f})")

        # Check if current spend exceeds threshold
        if current_spend > COST_THRESHOLD:
            subject = f"🚨 AWS Cost Alert: Spending Threshold Exceeded (${current_spend:.2f} {currency})"
            message = (
                f"AWS Cost Alert Notification\n\n"
                f"Your Month-to-Date (MTD) AWS spend has exceeded your threshold.\n\n"
                f"• Current Spend: ${current_spend:.4f} {currency}\n"
                f"• Configured Threshold: ${COST_THRESHOLD:.2f} {currency}\n"
                f"• Time Period Evaluated: {start_date} to {end_date}\n\n"
                f"Please review your active AWS resources to prevent unexpected billing."
            )

            logger.info(f"Threshold exceeded! Publishing SNS alert to: {SNS_TOPIC_ARN}")
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject=subject,
                Message=message
            )
            
            return {
                "statusCode": 200,
                "body": f"Alert triggered! MTD Spend (${current_spend:.2f}) exceeded threshold (${COST_THRESHOLD:.2f})."
            }

        else:
            logger.info(f"Spend is within limit (${current_spend:.2f} <=${COST_THRESHOLD:.2f}). No alert sent.")
            return {
                "statusCode": 200,
                "body": f"Spend OK. MTD Spend (${current_spend:.2f}) is below threshold (${COST_THRESHOLD:.2f})."
            }

    except Exception as e:
        logger.error(f"Error evaluating Cost Explorer metrics: {str(e)}")
        raise e