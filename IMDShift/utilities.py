import click
import sys

from .AWS import AWS_Utils
from .AWS import EC2, Sagemaker, ASG, Lightsail, ECS, EKS, Beanstalk


SERVICES_LIST = ['EC2', 'SAGEMAKER', 'ASG', 'LIGHTSAIL', 'ECS', 'EKS', 'BEANSTALK', 'AUTOSCALING']

class ScanRegion():
    def __init__(self, included_regions=None, excluded_regions=None, profile=None, role_arn=None):
        self.aws_utils = AWS_Utils()
        self.all_regions = self.aws_utils.get_enabled_regions(profile, role_arn)
        self.included_regions = included_regions or "ALL"
        self.excluded_regions = excluded_regions or []

        if isinstance(self.included_regions, str):
            self.included_regions = self.included_regions.split(",")
            if "ALL" not in self.included_regions:
                self.included_regions = [region.strip(" ") for region in self.included_regions]
            else:
                self.scan_regions = self.all_regions
        else:
            self.included_regions = list(self.included_regions)

        self.scan_regions = []

        if "ALL" in self.included_regions:
            self.scan_regions = self.all_regions
        else:
            for region in self.included_regions:
                if region in self.all_regions:
                    self.scan_regions.append(region)

        if isinstance(self.excluded_regions, str):
            self.excluded_regions = self.excluded_regions.split(",")
            if "ALL" in self.included_regions:
                self.excluded_regions = [region.strip(" ") for region in self.excluded_regions]
                self.scan_regions = [region for region in self.all_regions if region not in self.excluded_regions]
            else:
                for region in self.excluded_regions:
                    region = region.strip(" ")
                    if region in self.scan_regions:
                        self.scan_regions.remove(region)

        if not self.scan_regions:
            print("No regions to scan.")
            return

    def result(self):
        return self.scan_regions


def check_imdsv1_usage(regions=None, profile=None, role_arn=None):
    ec2_obj = EC2(regions=regions, profile=profile, role_arn=role_arn)
    ec2_obj.generate_imdsv1_usage_result()

    sys.exit(0)


def trigger_scan(services, regions=None, migrate=False, \
                 update_hop_limit=None, enable_imds=False, \
                    profile = None, role_arn=None):

        for service in SERVICES_LIST:

            if service in services:
                click.echo(f"\n[+] Fetching all {service} resources")

                services.pop(services.index(service))

                if service == 'EC2':
                    ec2_obj = EC2(regions=regions, profile=profile, role_arn=role_arn)
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
                    ec2_obj = EC2(regions=None, profile=profile, role_arn=role_arn)
                    ecs_obj = ECS(regions=regions, ec2_obj=ec2_obj, profile=profile, role_arn=role_arn)
                    ecs_obj.generate_results()
                    ecs_obj.ecs 
                    if update_hop_limit != None:
                        ec2_obj.update_hop_limit_for_resources(update_hop_limit)

                        if enable_imds:
                            ec2_obj.enable_metadata_for_resources(update_hop_limit)

                        if migrate:
                            ec2_obj.migrate_resources(update_hop_limit)

                    else:
                        if enable_imds:
                            ec2_obj.enable_metadata_for_resources()

                        if migrate:
                            ec2_obj.migrate_resources()
                
                
                elif service == "EKS":
                    ec2_obj = EC2(region=None, profile=profile, role_arn=role_arn)
                    eks_obj = EKS(regions=regions, ec2_obj=ec2_obj, profile=profile, role_arn=role_arn)
                    eks_obj.generate_results()

                    if update_hop_limit != None:
                        ec2_obj.update_hop_limit_for_resources(update_hop_limit)

                        if enable_imds:
                            ec2_obj.enable_metadata_for_resources(update_hop_limit)

                        if migrate:
                            ec2_obj.migrate_resources(update_hop_limit)

                    else:
                        if enable_imds:
                            ec2_obj.enable_metadata_for_resources()

                        if migrate:
                            ec2_obj.migrate_resources()


                elif service == "ASG" or service == "AUTOSCALING":
                    ec2_obj = EC2(region=None, profile=profile, role_arn=role_arn)
                    asg_obj = ASG(regions=regions, ec2_obj=ec2_obj, profile=profile, role_arn=role_arn)
                    asg_obj.generate_results()
                
                    if update_hop_limit != None:
                        ec2_obj.update_hop_limit_for_resources(update_hop_limit)

                        if enable_imds:
                            ec2_obj.enable_metadata_for_resources(update_hop_limit)

                        if migrate:
                            ec2_obj.migrate_resources(update_hop_limit)

                    else:
                        if enable_imds:
                            ec2_obj.enable_metadata_for_resources()

                        if migrate:
                            ec2_obj.migrate_resources()


                elif service == 'LIGHTSAIL':
                    lightsail_obj = Lightsail(regions=regions, profile=profile, role_arn=role_arn)
                    lightsail_obj.generate_result()

                    if update_hop_limit != None:
                        lightsail_obj.update_hop_limit_for_resources(update_hop_limit)

                        if enable_imds:
                            lightsail_obj.enable_metadata_for_resources(update_hop_limit)

                        if migrate:
                            lightsail_obj.migrate_resources(update_hop_limit)

                    else:
                        if enable_imds:
                            lightsail_obj.enable_metadata_for_resources(update_hop_limit)

                        if migrate:
                            lightsail_obj.migrate_resources(update_hop_limit)


                elif service == 'SAGEMAKER':
                    sagemaker_obj = Sagemaker(regions=regions, profile=profile, role_arn=role_arn)
                    sagemaker_obj.generate_result()

                    if migrate: 
                        sagemaker_obj.migrate_resources()

def print_policies():
    SCPS_STRINGS = """
    * Require role credentials for an EC2 to have been retrieved using the IMDSv2, credentials fetched from IMDSv1 would result in an "AccessDenied" error:
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "RequireAllEc2RolesToUseV2",
                    "Effect": "Deny",
                    "Action": "*",
                    "Resource": "*",
                    "Condition": {
                        "NumericLessThan": {
                            "ec2:RoleDelivery": "2.0"
                        }
                    }
                }
            ]
        }

    * Ensure that EC2s can only be created if you enforce that they use IMDSv2:
        {
            "Version": "2012-10-17",
            "Statement": {
                "Sid": "RequireImdsV2",
                "Effect": "Deny",
                "Action": "ec2:RunInstances",
                "Resource": "arn:aws:ec2:*:*:instance/*",
                "Condition": {
                    "StringNotEquals": {
                        "ec2:MetadataHttpTokens": "required"
                    }
                }
            }
        }

    * Deny option to change type of metadata:
        {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Deny",
                "Action": "ec2:ModifyInstanceMetadataOptions",
                "Resource": "*"
            }
        }

    * Ensure the hop count that can be set is restricted:
        {
            "Version": "2012-10-17",
            "Statement": {
                "Sid": "MaxImdsHopLimit",
                "Effect": "Deny",
                "Action": "ec2:RunInstances",
                "Resource": "arn:aws:ec2:*:*:instance/*",
                "Condition": {
                    "NumericGreaterThan": {"ec2:MetadataHttpPutResponseHopLimit": "1"}
                }
            }
        }

    * Ensure Sagemaker notebooks created/updated use IMDSv2
        {
        "Sid": "AllowSagemakerWithIMDSv2Only",
        "Effect": "Allow",
        "Action":
        [
            "sagemaker:CreateNotebookInstance",
            "sagemaker:UpdateNotebookInstance"
        ],
        "Resource": "*",
        "Condition":
        {
            "StringEquals":
            {
                "sagemaker:MinimumInstanceMetadataServiceVersion": "2"
            }
        }
    }
    """

    click.secho("[+] The following SCPs can be used either with an IAM policy or as an organisation Service Control Policy (SCP).")
    click.secho("[+] Printing SCPs associated with IMDS usage.")
    click.secho(f"{SCPS_STRINGS}", bold=True, fg='green')


    click.secho("[+] References for the SCPs:")
    click.secho("  * https://cloudsecdocs.com/aws/services/iam/organizations/#sample-scps:~:text=Require%20role%20credentials%20for%20an%20EC2%20to%20have%20been%20retrieved%20using%20the%20IMDSv2%3A", fg='yellow')
    click.secho("  * https://aws.amazon.com/blogs/machine-learning/amazon-sagemaker-notebook-instances-now-support-configuring-and-restricting-imds-versions/", fg='yellow')


    sys.exit(0)


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
