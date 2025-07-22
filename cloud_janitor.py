import boto3
import click
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
from datetime import datetime, timedelta, timezone

# We need the kubernetes client library for the new command.
# If you don't have it, run: pip install kubernetes
try:
    from kubernetes import client, config
    from kubernetes.config.config_exception import ConfigException
except ImportError:
    print("The 'kubernetes' library is not installed. Please run 'pip install kubernetes' to use Kubernetes features.")
    exit(1)


# --- Core Logic Functions ---

def find_unattached_volumes(ec2_client):
    """Finds all EBS volumes in the 'available' state."""
    return ec2_client.describe_volumes(
        Filters=[{'Name': 'status', 'Values': ['available']}]
    )['Volumes']

def find_old_snapshots(ec2_client, days_older):
    """Finds all EBS snapshots older than a specified number of days."""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_older)
    response = ec2_client.describe_snapshots(OwnerIds=['self'])
    old_snapshots = [snap for snap in response['Snapshots'] if snap['StartTime'] < cutoff_date]
    return old_snapshots

def find_root_workloads(k8s_client):
    """
    Finds all pods in the cluster that are running as the root user.
    
    Args:
        k8s_client: An initialized Kubernetes API client.
        
    Returns:
        A list of dictionaries, each representing a pod running as root.
    """
    insecure_pods = []
    # v1.list_pod_for_all_namespaces() is the function to get all pods in the cluster.
    all_pods = k8s_client.list_pod_for_all_namespaces(watch=False)
    
    for pod in all_pods.items:
        # We check the security context of each container within the pod.
        for container in pod.spec.containers:
            # If security_context is None or run_as_user is 0, it's likely running as root.
            if not container.security_context or container.security_context.run_as_user == 0:
                insecure_pods.append({
                    'name': pod.metadata.name,
                    'namespace': pod.metadata.namespace,
                    'container': container.name
                })
                # Once we find one insecure container, we can move to the next pod.
                break 
    return insecure_pods


# --- CLI Command Group ---

@click.group()
def cli():
    """
    Cloud Janitor: A read-only tool to find unused or insecure resources.
    """
    pass


# --- AWS Commands ---

@cli.command('find-unused-ebs')
@click.option('--region', default='us-east-1', help='The AWS region to scan.', show_default=True)
def find_unused_ebs_command(region):
    """Finds and lists all unattached EBS volumes."""
    click.echo(f"-> Searching for unattached EBS volumes in region: {region}...")
    try:
        ec2_client = boto3.client('ec2', region_name=region)
        unattached_volumes = find_unattached_volumes(ec2_client)
        
        if not unattached_volumes:
            click.secho("--> No unattached volumes found.", fg='green')
            return
            
        click.secho(f"--> Found {len(unattached_volumes)} unattached volume(s):", fg='yellow')
        click.echo(f"{'Volume ID':<22} {'Size (GB)':<12} {'Created On':<28}")
        click.echo(f"{'--'*11:<22} {'--'*6:<12} {'--'*14:<28}")
        
        total_size = 0
        for vol in unattached_volumes:
            click.echo(f"{vol['VolumeId']:<22} {str(vol['Size']):<12} {vol['CreateTime'].strftime('%Y-%m-%d %H:%M:%S'):<28}")
            total_size += vol['Size']
            
        click.secho(f"\nTotal size of unattached volumes: {total_size} GB", fg='yellow')

    except (NoCredentialsError, PartialCredentialsError):
        click.secho("ERROR: AWS credentials not found.", fg='red')
    except ClientError as e:
        click.secho(f"ERROR: An AWS client error occurred: {e}", fg='red')
    except Exception as e:
        click.secho(f"An unexpected error occurred: {e}", fg='red')


@cli.command('find-old-snapshots')
@click.option('--region', default='us-east-1', help='The AWS region to scan.', show_default=True)
@click.option('--days', 'days_older', default=90, help='The age of snapshots in days to be considered old.', show_default=True)
def find_old_snapshots_command(region, days_older):
    """Finds and lists EBS snapshots older than a specified number of days."""
    click.echo(f"-> Searching for snapshots older than {days_older} days in region: {region}...")
    try:
        ec2_client = boto3.client('ec2', region_name=region)
        old_snapshots = find_old_snapshots(ec2_client, days_older)
        
        if not old_snapshots:
            click.secho(f"--> No snapshots found older than {days_older} days.", fg='green')
            return
            
        click.secho(f"--> Found {len(old_snapshots)} snapshot(s) older than {days_older} days:", fg='yellow')
        click.echo(f"{'Snapshot ID':<22} {'Size (GB)':<12} {'Created On':<28} {'Description'}")
        click.echo(f"{'--'*11:<22} {'--'*6:<12} {'--'*14:<28} {'--'*15}")
        
        total_size = 0
        for snap in old_snapshots:
            description = snap.get('Description', 'N/A')
            if len(description) > 40:
                description = description[:37] + '...'
            
            click.echo(f"{snap['SnapshotId']:<22} {str(snap['VolumeSize']):<12} {snap['StartTime'].strftime('%Y-%m-%d %H:%M:%S'):<28} {description}")
            total_size += snap['VolumeSize']
            
        click.secho(f"\nTotal size of old snapshots: {total_size} GB", fg='yellow')

    except (NoCredentialsError, PartialCredentialsError):
        click.secho("ERROR: AWS credentials not found.", fg='red')
    except ClientError as e:
        click.secho(f"ERROR: An AWS client error occurred: {e}", fg='red')
    except Exception as e:
        click.secho(f"An unexpected error occurred: {e}", fg='red')


# --- NEW Kubernetes Command ---

@cli.command('find-insecure-workloads')
def find_insecure_workloads_command():
    """Finds pods in the current K8s cluster running as the root user."""
    click.echo("-> Connecting to Kubernetes cluster...")
    try:
        # This loads your Kubernetes configuration from the default location (~/.kube/config).
        config.load_kube_config()
        # This creates a client object to interact with the Kubernetes API.
        k8s_client = client.CoreV1Api()
        
        click.echo("-> Scanning for pods running as root...")
        insecure_pods = find_root_workloads(k8s_client)
        
        if not insecure_pods:
            click.secho("--> No pods found running as root. Your cluster workloads look secure!", fg='green')
            return
            
        click.secho(f"--> Found {len(insecure_pods)} pod(s) running as root:", fg='red')
        click.echo(f"{'NAMESPACE':<25} {'POD NAME':<35} {'CONTAINER NAME'}")
        click.echo(f"{'--'*12:<25} {'--'*17:<35} {'--'*15}")
        
        for pod in insecure_pods:
            click.echo(f"{pod['namespace']:<25} {pod['name']:<35} {pod['container']}")

    except ConfigException:
        click.secho("ERROR: Kubernetes config file not found.", fg='red')
        click.echo("Please ensure you have a valid kubeconfig file (e.g., ~/.kube/config).")
    except Exception as e:
        click.secho(f"An unexpected error occurred: {e}", fg='red')


if __name__ == '__main__':
    cli()
