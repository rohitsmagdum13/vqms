Title: Provision AWS S3, SQS, and EventBridge resources for VQMS Dev

Ticket Type: Infrastructure / Cloud Setup

Priority: High

Description:
Please provision the following AWS resources in us-east-1 for the Vendor Query Management System (VQMS) development environment.

S3 Buckets

vqms-email-raw-dev
vqms-email-attachments-dev
vqms-audit-artifacts-dev
vqms-knowledge-artifacts-dev

SQS Queues

vqms-email-intake-queue-dev
vqms-query-intake-queue-dev
vqms-dlq-dev

EventBridge

vqms-event-bus-dev

Requested AWS Commands

# S3 Buckets
aws s3 mb s3://vqms-email-raw-dev --region us-east-1
aws s3 mb s3://vqms-email-attachments-dev --region us-east-1
aws s3 mb s3://vqms-audit-artifacts-dev --region us-east-1
aws s3 mb s3://vqms-knowledge-artifacts-dev --region us-east-1

# SQS Queues
aws sqs create-queue --queue-name vqms-email-intake-queue-dev --region us-east-1
aws sqs create-queue --queue-name vqms-query-intake-queue-dev --region us-east-1
aws sqs create-queue --queue-name vqms-dlq-dev --region us-east-1

# EventBridge Bus
aws events create-event-bus --name vqms-event-bus-dev --region us-east-1

Purpose / Business Need:
These resources are required to establish the base AWS infrastructure for the VQMS dev environment:

Store raw inbound vendor emails
Store email attachments
Store audit artifacts
Store knowledge artifacts
Queue inbound email/query processing events
Support dead-letter handling for failed messages
Enable event-driven communication through EventBridge

Acceptance Criteria:

All 4 S3 buckets are created successfully in us-east-1
All 3 SQS queues are created successfully in us-east-1
EventBridge bus vqms-event-bus-dev is created successfully
Resource names exactly match the requested naming convention
Bucket names, queue URLs/ARNs, and event bus ARN are shared after creation