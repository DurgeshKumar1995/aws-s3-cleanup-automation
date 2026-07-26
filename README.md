# AWS Automation Suite (Lambda & Boto3)

This repository contains production-ready serverless automation solutions built with **AWS Lambda (Python 3.12)**, **Boto3**, and **Amazon EventBridge**. Each pattern enforces least-privilege IAM policies, structured CloudWatch logging, and automated infrastructure management.

---

## 📋 General Prerequisites & Cost Safeguards

* **Region Standard**: All resources deployed in a single region (e.g., `us-east-1` or `ap-south-1`).
* **Budget Safeguard**: $1.00 USD AWS Budget Alert active in Billing & Cost Management.
* **Instance Tier**: `t3.micro` / `t2.micro` (free-tier eligible).
* **Teardown Protocol**: Terminate/delete all EC2 instances, EBS volumes, S3 buckets, and EventBridge rules immediately after capturing test screenshots.

---

## 📁 Repository Structure

```text
aws-automation-suite/
│
├── README.md                          # Comprehensive documentation
├── ec2-scheduler /
│   ├── lambda_function.py             # Nightly Stop / Morning Start script
│   └── policy.json                    # Inline least-privilege IAM policy
├── assignment-1-s3-bucket-cleanup/
│   ├── lambda_function.py             # s3 bucket cleanup function
│   └── policy.json                    # Inline least-privilege IAM policy
├── assignment-2-ec2-snapshot/
│   ├── lambda_function.py             # ebs sanpshot cleanup
│   └── policy.json                    # Inline least-privilege IAM policy
├── assignment-3-auto-tagging-ec2/
│   ├── lambda_function.py             # auto tagging ec2
│   └── policy.json                    # Inline least-privilege IAM policy
├── assignment-4-Daily -AWS-Cost-Alert/
│   ├── lambda_function.py             # alert daily
│   └── policy.json                    # Inline least-privilege IAM policy
├── assignment-5-restore-ec2-instance/
│   ├── lambda_function.py             # restore ec2 intance
│   └── policy.json                    # Inline least-privilege IAM policy
├── assignment-6-audit-s3-bucket/
│   ├── lambda_function.py             # audit s3 bucket
│   └── policy.json                    # Inline least-privilege IAM policy
└── screenshots/                       # Verification evidence
    ├── assignment-1/
    ├── assignment-2/
    ├── assignment-3/
    ├── assignment-4/
    ├── assignment-5/
    ├── assignment-6/
    └── ec2-scheduler/

```

## 📌 EC2 Auto-Scheduler (Nightly Stop / Morning Start)
### Overview
Automates stopping dev EC2 instances at night and starting them in the morning based on EventBridge schedules and custom JSON payloads

``` [ EventBridge Cron ] ──(Payload: START/STOP)──> [ Lambda ] ──> [ Target EC2 (Environment=Dev) ] ```


### EventBridge Configuration
```Nightly Stop: Cron cron(0 19 * * ? *) | JSON Payload: {"action": "STOP"}```

```Morning Start: Cron cron(0 7 * * ? *) | JSON Payload: {"action": "START"}```


## 📌 Assignment 1:
# AWS Automation: Automated S3 Bucket Cleanup (Objects > 30 Days)

## 📌 Project Overview
This project delivers a serverless, automated cleanup pattern built with **AWS Lambda (Python 3.12)**, **Boto3**, and **Amazon EventBridge**. It periodically scans a targeted Amazon S3 bucket, compares each object's UTC timestamp (`LastModified`) against a 30-day threshold, and deletes stale files. This prevents unbounded storage growth and lowers AWS monthly costs.

---

## 🛠️ Architecture & Workflow

```text
[ EventBridge Cron Rule ] ──(Daily Trigger)──> [ AWS Lambda ] ──> [ Target S3 Bucket ]
   └── cron(0 2 * * ? *)                         ├── List objects (Paginator)
                                                 ├── Compare LastModified vs UTC Cutoff
                                                 └── Delete objects older than 30 days

```

## 📌 Assignment 2:
## AWS Automation: Automated EBS Snapshot Creation and Cleanup

## 📌 Project Overview
This solution automates EBS volume backups and lifecycle retention using **AWS Lambda (Python 3.12)**, **Boto3**, and **Amazon EventBridge**. It takes a point-in-time snapshot of a specified EBS volume, applies standard tags, scans existing volume backups owned by the account, and purges snapshots older than 30 days.

---

## 🛠️ Architecture & Workflow

```text
[ EventBridge Cron Rule ] ──(Weekly Trigger)──> [ AWS Lambda ] ──> [ EBS Volume ]
   └── cron(0 0 ? * 1 *)                           ├── Create & Tag Snapshot
                                                   └── Delete Snapshots > 30 Days
```

## 📌 Assignment 3:
# AWS Automation: Auto-Tagging EC2 Instances on Launch

## 📌 Project Overview
This solution delivers an event-driven compliance pattern using **AWS Lambda (Python 3.12)**, **Boto3**, and **Amazon EventBridge**. Whenever a new EC2 instance enters the `running` state, EventBridge triggers Lambda to instantly enrich the instance with standardized metadata (`LaunchDate`, `Environment`, `ManagedBy`, `Owner`).

---

## 🛠️ Architecture & Workflow

```text
[ EC2 Launch ] ──> [ EventBridge Rule (State: running) ] ──> [ Lambda ] ──> [ Apply Tags to EC2 ]
                                                               └── (Optional) CloudTrail User Lookup
```

## 📌 Assignment 4:
## AWS Automation: Daily AWS Cost Alert Using Cost Explorer API and SNS

## 📌 Project Overview
This solution delivers an automated billing monitoring solution using **AWS Lambda (Python 3.12)**, **Boto3**, **AWS Cost Explorer API**, and **Amazon SNS**. It queries month-to-date (MTD) unblended costs daily and sends immediate email notifications via SNS when spending exceeds a defined threshold.

---

## 🛠️ Architecture & Workflow

```text
[ EventBridge Cron Rule ] ──(Daily Trigger)──> [ AWS Lambda ] ──> [ Cost Explorer API ]
   └── cron(0 8 * * ? *)                         │                  (ce:GetCostAndUsage)
                                                 └── (If Spend > $50)
                                                          │
                                                          ▼
                                                  [ Amazon SNS Topic ] ──> [ Email Alert ]

