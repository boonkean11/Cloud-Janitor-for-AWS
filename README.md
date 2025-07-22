# Cloud Janitor for AWS and Kubernetes

Cloud Janitor is a command-line interface (CLI) tool designed to help identify unused or insecure resources in your AWS and Kubernetes environments. It's a read-only tool, meaning it will only report findings and will not make any changes to your infrastructure.

## Features

Currently, Cloud Janitor provides the following functionalities:

*   **Find Unattached EBS Volumes (AWS):** Identifies EBS volumes that are in an 'available' state, meaning they are not attached to any EC2 instance and might be costing you money.
*   **Find Old EBS Snapshots (AWS):** Lists EBS snapshots older than a specified number of days, helping you manage storage costs and compliance.
*   **Find Insecure Kubernetes Workloads:** Scans your Kubernetes cluster for pods running as the root user, which can be a security risk.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/boonkean11/Cloud-Janitor-for-AWS.git
    cd Cloud-Janitor-for-AWS
    ```

2.  **Install dependencies:**
    Cloud Janitor requires `boto3`, `click`, and `kubernetes`.
    ```bash
    pip install boto3 click kubernetes
    ```

## AWS Credentials Setup

To use the AWS-related commands, you need to configure your AWS credentials. The `boto3` library (used by this tool) looks for credentials in the following order:

1.  **Environment Variables:** `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_SESSION_TOKEN`.
2.  **Shared Credential File:** `~/.aws/credentials` (e.g., created by `aws configure`).
3.  **AWS Config File:** `~/.aws/config`.
4.  **IAM Role for EC2 Instance:** If running on an EC2 instance with an assigned IAM role.

The easiest way to get started is by running `aws configure` in your terminal and providing your Access Key ID, Secret Access Key, and default region.

## Kubernetes Configuration

To use the Kubernetes command, you need to have your `kubeconfig` file set up correctly. The tool uses the default `kubeconfig` location (`~/.kube/config`). Ensure your `kubeconfig` points to the cluster you wish to scan and that you have the necessary permissions to list pods.

## Usage

All commands are run using the `cloud_janitor.py` script followed by the command name.

```bash
python cloud_janitor.py [command] --options
```

### 1. Find Unattached EBS Volumes

This command scans a specified AWS region for EBS volumes that are not attached to any EC2 instance.

```bash
python cloud_janitor.py find-unused-ebs --region us-east-1
```

*   `--region`: (Optional) The AWS region to scan. Defaults to `us-east-1`.

### 2. Find Old EBS Snapshots

This command finds EBS snapshots older than a specified number of days in a given AWS region.

```bash
python cloud_janitor.py find-old-snapshots --region us-east-1 --days 90
```

*   `--region`: (Optional) The AWS region to scan. Defaults to `us-east-1`.
*   `--days`: (Optional) The age of snapshots in days to be considered old. Defaults to `90`.

### 3. Find Insecure Kubernetes Workloads

This command connects to your configured Kubernetes cluster and identifies pods that are running as the root user.

```bash
python cloud_janitor.py find-insecure-workloads
```

*   This command does not require any additional options. It uses your local `kubeconfig` file.

---
**Note:** This tool is for auditing purposes only. It does not delete or modify any resources. Always review the output carefully and exercise caution when making changes to your cloud infrastructure.