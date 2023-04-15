import boto3
import click
import json
import os
import sys
from prettytable import PrettyTable
from time import sleep
from tqdm import tqdm


DEBUG = True


class AWS_Utils():

    def get_enabled_regions(self):
        client = boto3.client('ec2')
        enabled_regions = [region['RegionName']\
                           for region in client.describe_regions()['Regions']\
                            if region['OptInStatus'] in ["opt-in-not-required", "opted-in"]]
        
        return enabled_regions

    def generate_client(self, resource, region):
        client_obj = boto3.client(resource, region_name=region)
        return client_obj

        
class EC2():
    
    def __init__(self, regions=None) -> None:
        self.regions = regions
        self.aws_utils = AWS_Utils()
        self.ec2 = None
        self.resource_list = list()
        self.resources_with_imds_v1 = list()
        self.resource_with_metadata_disabled = list()
        self.resources_with_hop_limit_1 = list()
    
    def generate_result(self):
        for region in self.regions:
            print(region)
            self.process_result(region)
    
    def process_result(self, region):
        self.ec2 = self.aws_utils.generate_client("ec2", region)
        instances_details = self.ec2.describe_instances()['Reservations']
        for instance in instances_details:
            instance = instance["Instances"]
            self.resource_list += instance
        self.analyse_resources()
    

    def analyse_resources(self):

        progress_bar_with_resources = tqdm(self.resource_list, desc=f"[+] Analysing EC2 resources", colour='green', unit=' resources')
        
        for resource in progress_bar_with_resources:
            if resource['MetadataOptions']['HttpEndpoint'] == 'disabled':
                self.resource_with_metadata_disabled.append(resource)

            if resource['MetadataOptions']['HttpTokens'] != 'required':
                self.resources_with_imds_v1.append(resource)

            if resource['MetadataOptions']['HttpPutResponseHopLimit'] == 1:
                self.resources_with_hop_limit_1.append(resource)


        stats_table = PrettyTable()
        stats_table.align = 'c' 
        stats_table.valign = 'c' 
        stats_table.field_names = ['Metadata Disabled', 'IMDSv1 Enabled', 'Hop Limit = 1', 'Total Resources']
        stats_table.add_row(
            [
                len(self.resource_with_metadata_disabled),
                len(self.resources_with_imds_v1),
                len(self.resources_with_hop_limit_1),
                len(self.resource_list)
            ]
        )


        # click.echo(f"[+] Analysed all EC2 resources")
        click.echo(f"[+] Statistics from analysis:")
        click.secho(stats_table.get_string(), bold=True, fg='yellow')

    def enable_metadata_for_resources(self, hop_limit=None, all_resource=None, resource_list=None):
        click.echo(f"[+] Enabling metadata endpoint for resources for which it is disabled")
        progress_bar_with_resources = tqdm(self.resource_with_metadata_disabled, desc=f"[+] Enabling metadata for EC2 resources", colour='green', unit=' resources')
        
        for resource in progress_bar_with_resources:
            region = resource['Placement']['AvailabilityZone'][:-1]
            response = self.ec2.modify_instance_metadata_options(
                InstanceId = resource['InstanceId'],
                HttpTokens = 'required',
                HttpPutResponseHopLimit = hop_limit if hop_limit != None else 2,
                HttpEndpoint = 'enabled',
                HttpProtocolIpv6 = 'disabled',
                InstanceMetadataTags = 'disabled'
            )

    
    def update_hop_limit_for_resources(self, hop_limit=None, all_resource=None, resource_list=None):
        click.echo(f"[+] Updating hop limit for resources with metadata enabled")
        #DEBUG
        if resource_list == None:
            resource_list = all_resource
        progress_bar_with_resources = tqdm(self.resources_with_hop_limit_1, desc=f"[+] Updating hop limit for EC2 resources to {hop_limit}", colour='green', unit=' resources')
        for resource in progress_bar_with_resources:
            response = self.ec2.modify_instance_metadata_options(
                InstanceId = resource['InstanceId'],
                HttpTokens = 'required',
                HttpPutResponseHopLimit = hop_limit if hop_limit != None else 2,
                HttpEndpoint = 'enabled',
                HttpProtocolIpv6 = 'disabled',
                InstanceMetadataTags = 'disabled'
            )



    def migrate_resources(self, hop_limit=None):
        click.echo(f"[+] Performing migration of EC2 resources to IMDSv2")
        progress_bar_with_resources = tqdm(self.resource_list, desc=f"[+] Migrating all EC2 resources to IMDSv2", colour='green', unit=' resources')
        for resource in progress_bar_with_resources:
                
            if resource not in self.resource_with_metadata_disabled and resource not in  self.resources_with_hop_limit_1:
                region = resource['Placement']['AvailabilityZone'][:-1]
                os.environ['AWS_DEFAULT_REGION'] = region

                response = self.client.modify_instance_metadata_options(
                    InstanceId = resource['InstanceId'],
                    HttpTokens = "required",
                    HttpPutResponseHopLimit = hop_limit if hop_limit != None else 2,
                    HttpEndpoint = 'enabled',
                    HttpProtocolIpv6 = 'disabled',
                    InstanceMetadataTags = 'disabled'
                )


class Sagemaker():

    def __init__(self) -> None:
        ...


    def list_resources(self):
        ...


    def analyse_resources(self):
        ...


    def enable_metadata_for_resources(self):
        ...

    
    def update_hop_limit_for_resources(self):
        ...


    def migrate_resources(self):
        ...


class ASG():

    def __init__(self) -> None:
        ...


    def list_resources(self):
        ...


    def analyse_resources(self):
        ...


    def enable_metadata_for_resources(self):
        ...

    
    def update_hop_limit_for_resources(self):
        ...


    def migrate_resources(self):
        ...


class Lightsail():

    def __init__(self) -> None:
        ...


    def list_resources(self):
        ...


    def analyse_resources(self):
        ...


    def enable_metadata_for_resources(self):
        ...

    
    def update_hop_limit_for_resources(self):
        ...


    def migrate_resources(self):
        ...


class ECS():
    

    def __init__(self, regions=None) -> None:
        self.regions = regions
        self.aws_utils = AWS_Utils()
    
    # Return main result
    def process_result(self, region):
        ec2 = self.aws_utils.generate_client("ec2", region)
        ecs = self.aws_utils.generate_client("ecs", region)
        clusters = self.list_resources(ecs)
        instance_data = self.container_instance(clusters, ecs, ec2)
        print(len(instance_data))
        ec2_obj = EC2()
        ec2_obj.resource_list = instance_data
        ec2_obj.analyse_resources()

    # Seggregates regions and then process it accordingly
    def generate_results(self):
        for region in self.regions:
            print(region)
            self.process_result(region)
                

    def list_resources(self, ecs):
        result = []
        marker = None
        while True:
            if marker:
                arns = ecs.list_clusters(
                    nextToken=marker
                )["clusterArns"]
                for cluster in arns:
                    result.append(cluster)
            
            else:
                arns = ecs.list_clusters()["clusterArns"]
                for cluster in arns:
                    result.append(cluster)
            
            if "nextToken" in arns:
                marker = arns["nextToken"]
            else:
                return result
                

    def container_instance(self, clusters, ecs, ec2):
        result = []
        for cluster in clusters:
            instances = ecs.list_container_instances(cluster=cluster)["containerInstanceArns"]
            if len(instances) > 0:
                describe_instance = ecs.describe_container_instances(cluster=cluster, containerInstances=instances)["containerInstances"]
                instance_id = [instance_id["ec2InstanceId"] for instance_id in describe_instance]
                instance_details = ec2.describe_instances(InstanceIds=instance_id)["Reservations"]
                for instance in instance_details:
                    instance = instance["Instances"]
                    result += instance
                
        return result

            


    def analyse_resources(self):
        ...


    def enable_metadata_for_resources(self):
        ...

    
    def update_hop_limit_for_resources(self):
        ...


    def migrate_resources(self):
        ...


class EKS():

    def __init__(self) -> None:
        ...


    def list_resources(self):
        ...


    def analyse_resources(self):
        ...


    def enable_metadata_for_resources(self):
        ...

    
    def update_hop_limit_for_resources(self):
        ...


    def migrate_resources(self):
        ...


class Beanstalk():

    def __init__(self) -> None:
        ...


    def list_resources(self):
        ...


    def analyse_resources(self):
        ...


    def enable_metadata_for_resources(self):
        ...

    
    def update_hop_limit_for_resources(self):
        ...


    def migrate_resources(self):
        ...


if __name__ == '__main__':
    aws_obj = AWS_Utils()
    # print(aws_obj.get_enabled_regions())

    ec2_obj = EC2()
    ec2_obj.analyse_resources()
