import click
import sys
import boto3

from time import sleep
from tqdm import tqdm

from .AWS import AWS_Utils
from .AWS import EC2, Sagemaker, ASG, Lightsail, ECS, EKS, Beanstalk


SERVICES_LIST = ['EC2', 'Sagemaker', 'ASG', 'Lightsail', 'ECS', 'EKS', 'Beanstalk']

class ScanRegion():
    def __init__(self, included_regions=None, excluded_regions=None):
        self.aws_utils = AWS_Utils()
        self.all_regions = self.aws_utils.get_enabled_regions()
        self.included_regions = included_regions or "ALL"
        self.excluded_regions = excluded_regions or []

        if isinstance(self.included_regions, str):
            self.included_regions = self.included_regions.split(" ")
            if self.included_regions != "ALL":
                self.included_regions = [region.strip(",") for region in self.included_regions]
        else:
            self.included_regions = list(self.included_regions)

        self.scan_regions = []
        if self.included_regions == "ALL":
            self.scan_regions = self.all_regions
        else:
            for region in self.included_regions:
                if region in self.all_regions:
                    self.scan_regions.append(region)
        
        if isinstance(self.excluded_regions, str):
            self.excluded_regions = self.excluded_regions.split(" ")
            if "ALL" in self.included_regions:
                for region in self.excluded_regions:
                    region = region.strip(",")
                    if region in self.all_regions:
                        self.all_regions.remove(region)
                for region in self.all_regions:
                    self.scan_regions.append(region)
            else:
                for region in self.excluded_regions:
                    region = region.strip(",")
                    if region in self.scan_regions:
                        self.scan_regions.remove(region)

        if not self.scan_regions:
            print("No regions to scan.")
            return
        print(f"Scanning regions: {', '.join(self.scan_regions)}")

        
    def result(self):
        return self.scan_regions


def trigger_scan(services, regions=None, migrate=False, \
                 update_hop_limit=None, enable_imds=False):

        for service in SERVICES_LIST:

            if service in services:
                click.echo(f"\n[+] Fetching all {service} resources")

                services.pop(services.index(service))

                if service == 'EC2':
                    ec2_obj = EC2(regions=regions)
                    ec2_obj.generate_result()

                    if update_hop_limit != None:
                        ec2_obj.update_hop_limit_for_resources(update_hop_limit)

                        if enable_imds:
                            ec2_obj.enable_metadata_for_resources(update_hop_limit)

                        if migrate:
                            ec2_obj.migrate_resources(update_hop_limit)

                    else:
                        if enable_imds:
                            ec2_obj.enable_metadata_for_resources(update_hop_limit)

                        if migrate:
                            ec2_obj.migrate_resources(update_hop_limit)

                
                elif service == "ECS":
                    ecs_obj = ECS(regions=regions)
                    ecs_obj.generate_results()
                    if update_hop_limit != None:
                        ecs_obj.update_hop_limit_for_resources(update_hop_limit)

                        if enable_imds:
                            ecs_obj.enable_metadata_for_resources(update_hop_limit)

                        if migrate:
                            ecs_obj.migrate_resources(update_hop_limit)

                    else:
                        if enable_imds:
                            ecs_obj.enable_metadata_for_resources()

                        if migrate:
                            ecs_obj.migrate_resources()
                


def validate_services(services):
    for service in services:
        if service not in SERVICES_LIST:
            click.secho(f"[!] {service} is not support in IMDShift!", bold=True, fg='red')
            sys.exit(1)


def validate_regions(regions):
    aws_obj = AWS_Utils()
    enabled_regions = aws_obj.get_enabled_regions()

    for region in regions:
        if region not in enabled_regions:
            click.secho(f'[!] "{region}" is either invalid region or is not enabled. Exiting.', bold=True, fg='red')
            sys.exit(1)
