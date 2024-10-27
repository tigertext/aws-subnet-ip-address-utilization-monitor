import boto3
import os
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    vpc_id = os.environ['VPC_ID']
    subnet_ids = os.environ['SUBNET_IDS'].split(',')
    namespace = os.environ['NAMESPACE']

    ec2 = boto3.client('ec2')
    cloudwatch = boto3.client('cloudwatch')

    try:
        response = ec2.describe_subnets(
            Filters=[
                {'Name': 'vpc-id', 'Values': [vpc_id]},
                {'Name': 'subnet-id', 'Values': subnet_ids}
            ]
        )

        for subnet in response['Subnets']:
            subnet_id = subnet['SubnetId']
            available_ip_count = subnet['AvailableIpAddressCount']
            cidr_block = subnet['CidrBlock']
            total_ip_count = 2 ** (32 - int(cidr_block.split('/')[1])) - 5  # Subtract 5 for reserved IPs

            subnet_name = subnet_id  # Default to subnet ID if no name tag
            for tag in subnet.get('Tags', []):
                if tag['Key'] == 'Name':
                    subnet_name = tag['Value']
                    break

            utilization_percentage = ((total_ip_count - available_ip_count) / total_ip_count) * 100

            # Send metrics to CloudWatch
            cloudwatch.put_metric_data(
                Namespace=namespace,
                MetricData=[
                    {
                        'MetricName': 'AvailableIPAddresses',
                        'Dimensions': [
                            {'Name': 'SubnetName', 'Value': subnet_name},
                            {'Name': 'SubnetId', 'Value': subnet_id}
                        ],
                        'Value': available_ip_count,
                        'Unit': 'Count'
                    },
                    {
                        'MetricName': 'IPUtilizationPercentage',
                        'Dimensions': [
                            {'Name': 'SubnetName', 'Value': subnet_name},
                            {'Name': 'SubnetId', 'Value': subnet_id}
                        ],
                        'Value': utilization_percentage,
                        'Unit': 'Percent'
                    }
                ]
            )

            print(f"Metrics sent for Subnet: {subnet_name} (ID: {subnet_id})")

    except ClientError as e:
        print(f"An error occurred: {e}")
        return {
            'statusCode': 500,
            'body': str(e)
        }

    return {
        'statusCode': 200,
        'body': 'Subnet monitoring completed'
    }
