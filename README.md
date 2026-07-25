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
├── assignment-1-ec2-scheduler/
│   ├── lambda_function.py             # Nightly Stop / Morning Start script
│   └── policy.json                    # Inline least-privilege IAM policy
├── assignment-2-ebs-cleanup/
│   ├── lambda_function.py             # Unattached volume cleaner
│   └── policy.json                    # Inline least-privilege IAM policy
├── assignment-3-s3-cleanup/
│   ├── lambda_function.py             # Stale file lifecycle cleaner
│   └── policy.json                    # Inline least-privilege IAM policy
├── assignment-4-auto-tagger/
│   ├── lambda_function.py             # Auto-tagger on instance launch
│   └── policy.json                    # Inline least-privilege IAM policy
└── screenshots/                       # Verification evidence
    ├── assignment-1/
    ├── assignment-2/
    ├── assignment-3/
    └── assignment-4/

```

## 📌 Assignment 1: EC2 Auto-Scheduler (Nightly Stop / Morning Start)
### Overview
Automates stopping dev EC2 instances at night and starting them in the morning based on EventBridge schedules and custom JSON payloads

``` [ EventBridge Cron ] ──(Payload: START/STOP)──> [ Lambda ] ──> [ Target EC2 (Environment=Dev) ] ```


### EventBridge Configuration
```Nightly Stop: Cron cron(0 19 * * ? *) | JSON Payload: {"action": "STOP"}```

```Morning Start: Cron cron(0 7 * * ? *) | JSON Payload: {"action": "START"}```

