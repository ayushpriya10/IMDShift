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

    def __init__(self) -> None:
        client = boto3.client('ec2')
        self.enabled_regions = \
            [region['RegionName']\
              for region in client.describe_regions()['Regions']\
                  if region['OptInStatus'] in ["opt-in-not-required", "opted-in"]]
        
    
    def get_enabled_regions(self):
        return self.enabled_regions


class EC2():

    client = boto3.client('ec2')
    resource_list = list()
    resources_with_imds_v1 = list()
    resource_with_metadata_disabled = list()
    resources_with_hop_limit_1 = list()


    def __init__(self, included_regions=None, excluded_regions=None) -> None:
        self.included_regions = included_regions
        self.excluded_regions = excluded_regions
        self.enabled_regions = AWS_Utils().get_enabled_regions()


    def list_resources(self):
        
        if self.included_regions == 'ALL':

            for region in self.enabled_regions:

                if self.excluded_regions != None and region in self.excluded_regions:
                    self.enabled_regions.pop(self.enabled_regions.index(region))
                    continue

                os.environ['AWS_DEFAULT_REGION'] = region
                self.resource_list += self.client.describe_instances()['Reservations'][0]['Instances']

            # if DEBUG:
            #     pass
            #     print(self.resource_list['ap-south-1']['Reservations'][0]['Instances'][0])
            #     print(f"All enabled regions: {AWS_Utils().get_enabled_regions()}")
            #     print(f"Enabled regions: {self.enabled_regions}")
            #     print(f"Resource list regions: {self.resource_list}")


        if self.included_regions != None and self.included_regions != 'ALL':

            for region in self.included_regions:

                os.environ['AWS_DEFAULT_REGION'] = region
                self.resource_list += self.client.describe_instances()['Reservations'][0]['Instances']

            # if DEBUG:
            #     pass
                # print(self.resource_list)
                # print(f"All enabled regions: {AWS_Utils().get_enabled_regions()}")
                # print(f"Enabled regions: {self.enabled_regions}")
                # print(f"Resource list regions: {self.resource_list}")



        # if DEBUG:
        #     pass
        #     with open('/Users/ayushpriya/work/Projects/IMDShift/IMDShift/testing_output/ec2-resources.json', 'w') as fh:
        #         fh.write(json.dumps(self.resource_list, default=str, indent=4))


    def analyse_resources(self):

        # if DEBUG:
        #     pass
        #     with open('/Users/ayushpriya/work/Projects/IMDShift/IMDShift/testing_output/ec2-resources.json') as fh:
        #         self.resource_list = json.loads(fh.read())

        progress_bar_with_resources = tqdm(self.resource_list, desc=f"[+] Analysing EC2 resources", colour='green', unit=' resources')
        for resource in progress_bar_with_resources:
            if resource['MetadataOptions']['HttpEndpoint'] == 'disabled':
                self.resource_with_metadata_disabled.append(resource)

            if resource['MetadataOptions']['HttpTokens'] != 'required':
                self.resources_with_imds_v1.append(resource)

            if resource['MetadataOptions']['HttpPutResponseHopLimit'] == 1:
                self.resources_with_hop_limit_1.append(resource)

        stats_table = PrettyTable()
        stats_table.align = 'c' # Horizontal Center Alignment
        stats_table.valign = 'c' # Vertical Center Alignment
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


    def enable_metadata_for_resources(self, hop_limit=None):
        click.echo(f"[+] Enabling metadata endpoint for resources for which it is disabled")
        progress_bar_with_resources = tqdm(self.resource_with_metadata_disabled, desc=f"[+] Enabling metadata for EC2 resources", colour='green', unit=' resources')
        for resource in progress_bar_with_resources:
            region = resource['Placement']['AvailabilityZone'][:-1]
            os.environ['AWS_DEFAULT_REGION'] = region

            response = self.client.modify_instance_metadata_options(
                InstanceId = resource['InstanceId'],
                HttpTokens = 'required',
                HttpPutResponseHopLimit = hop_limit if hop_limit != None else 2,
                HttpEndpoint = 'enabled',
                HttpProtocolIpv6 = 'disabled',
                InstanceMetadataTags = 'disabled'
            )

    
    def update_hop_limit_for_resources(self, hop_limit=None):
        click.echo(f"[+] Updating hop limit for resources with metadata enabled")
        progress_bar_with_resources = tqdm(self.resources_with_hop_limit_1, desc=f"[+] Updating hop limit for EC2 resources to {hop_limit}", colour='green', unit=' resources')
        for resource in progress_bar_with_resources:
            region = resource['Placement']['AvailabilityZone'][:-1]
            os.environ['AWS_DEFAULT_REGION'] = region

            response = self.client.modify_instance_metadata_options(
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
                    HttpTokens = 'required',
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
