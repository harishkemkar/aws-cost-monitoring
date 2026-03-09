import boto3
import logging
import time

# 1. Setup Logging
logging.basicConfig(
    filename='aws_cleanup.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='a'
)

def log_and_print(message):
    print(message)
    logging.info(message)

# Initialize a base client to fetch all regions
ec2_base = boto3.client('ec2', region_name='us-east-1')
regions = [region['RegionName'] for region in ec2_base.describe_regions()['Regions']]

log_and_print("Starting Global AWS Cleanup Sequence...")

for region in regions:
    log_and_print(f"\n--- PROCESSING REGION: {region} ---")
    
    # Regional Clients
    ec2 = boto3.client('ec2', region_name=region)
    ec2_res = boto3.resource('ec2', region_name=region)
    rds = boto3.client('rds', region_name=region)
    elbv2 = boto3.client('elbv2', region_name=region)
    eks = boto3.client('eks', region_name=region)

    # --- PHASE 1: RDS DELETION ---
    try:
        dbs = rds.describe_db_instances()['DBInstances']
        for db in dbs:
            db_id = db['DBInstanceIdentifier']
            log_and_print(f"Deleting RDS Instance: {db_id}")
            rds.delete_db_instance(DBInstanceIdentifier=db_id, SkipFinalSnapshot=True, DeleteAutomatedBackups=True)
    except Exception as e:
        logging.error(f"RDS Cleanup Error in {region}: {str(e)}")

    # --- PHASE 2: EC2 TERMINATION (Required to unlock VPC) ---
    try:
        instances = ec2.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['running', 'stopped', 'pending']}])
        instance_ids = [i['InstanceId'] for r in instances['Reservations'] for i in r['Instances']]
        if instance_ids:
            log_and_print(f"Terminating EC2 Instances: {instance_ids}")
            ec2.terminate_instances(InstanceIds=instance_ids)
            # Short wait for instances to enter 'shutting-down' state
            time.sleep(5) 
    except Exception as e:
        logging.error(f"EC2 Cleanup Error in {region}: {str(e)}")

    # --- PHASE 3: VPC DELETION & DEPENDENCIES ---
    try:
        vpcs = ec2.describe_vpcs()['Vpcs']
        for vpc_data in vpcs:
            if vpc_data.get('IsDefault'): continue  # Skip Default VPCs
            
            vpc_id = vpc_data['VpcId']
            vpc = ec2_res.Vpc(vpc_id)
            log_and_print(f"Cleaning VPC: {vpc_id}")

            # Detach/Delete IGWs
            for igw in vpc.internet_gateways.all():
                igw.detach_from_vpc(VpcId=vpc_id)
                igw.delete()
            
            # Delete Endpoints
            endpoints = ec2.describe_vpc_endpoints(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['VpcEndpoints']
            if endpoints:
                ec2.delete_vpc_endpoints(VpcEndpointIds=[ep['VpcEndpointId'] for ep in endpoints])

            # Delete Subnets
            for subnet in vpc.subnets.all():
                subnet.delete()

            # Delete Custom SGs
            for sg in vpc.security_groups.all():
                if sg.group_name != 'default': sg.delete()

            # Delete VPC
            vpc.delete()
    except Exception as e:
        logging.error(f"VPC Cleanup Error in {region}: {str(e)}")

    # --- PHASE 4: OTHER ITEMS ---
    # ELB Deletion
    try:
        for lb in elbv2.describe_load_balancers()['LoadBalancers']:
            log_and_print(f"Deleting ELB: {lb['LoadBalancerName']}")
            elbv2.delete_load_balancer(LoadBalancerArn=lb['LoadBalancerArn'])
    except Exception as e: logging.error(f"ELB Error: {str(e)}")

    # EKS Deletion
    try:
        for cluster in eks.list_clusters()['clusters']:
            log_and_print(f"Deleting EKS Cluster: {cluster}")
            eks.delete_cluster(name=cluster)
    except Exception as e: logging.error(f"EKS Error: {str(e)}")

    # Release EIPs
    try:
        for addr in ec2.describe_addresses()['Addresses']:
            if 'AllocationId' in addr:
                log_and_print(f"Releasing EIP: {addr['PublicIp']}")
                ec2.release_address(AllocationId=addr['AllocationId'])
    except Exception as e: logging.error(f"EIP Error: {str(e)}")

    # Delete Available EBS Volumes
    try:
        volumes = ec2.describe_volumes(Filters=[{'Name': 'status', 'Values': ['available']}])['Volumes']
        for vol in volumes:
            log_and_print(f"Deleting EBS Volume: {vol['VolumeId']}")
            ec2.delete_volume(VolumeId=vol['VolumeId'])
    except Exception as e: logging.error(f"EBS Error: {str(e)}")

log_and_print("\nGlobal Cleanup complete. Review 'aws_cleanup.log' for details.")
