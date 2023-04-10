import click
import sys

from time import sleep
from tqdm import tqdm

from .AWS import AWS_Utils
from .AWS import EC2, Sagemaker, ASG, Lightsail, ECS, EKS, Beanstalk


SERVICES_LIST = ['EC2', 'Sagemaker', 'ASG', 'Lightsail', 'ECS', 'EKS', 'Beanstalk']


def trigger_scan(services, included_regions='ALL', excluded_regions=None, migrate=False, \
                 update_hop_limit=None, enable_imds=False):

        for service in SERVICES_LIST:

            if service in services:
                click.echo(f"\n[+] Fetching all {service} resources")

                services.pop(services.index(service))

                if service == 'EC2':
                    ec2_obj = EC2(included_regions=included_regions, excluded_regions=excluded_regions)
                    ec2_obj.list_resources()
                    ec2_obj.analyse_resources()

                    if enable_imds:
                        ec2_obj.enable_metadata_for_resources()

                    if update_hop_limit != None:
                        ec2_obj.update_hop_limit_for_resources(update_hop_limit)

                    if migrate:
                        ec2_obj.migrate_resources()


def validate_services(services):
    for service in services:
        if service not in SERVICES_LIST:
            click.secho(f"[!] {service} is not support in IMDShift!", bold=True, fg='red')
            sys.exit(1)


def validate_regions(regions):
    aws_obj = AWS_Utils()
    enabled_regions = aws_obj.get_enabled_regions()

    # print(enabled_regions)

    for region in regions:
        if region not in enabled_regions:
            click.secho(f'[!] "{region}" is either invalid region or is not enabled. Exiting.', bold=True, fg='red')
            sys.exit(1)