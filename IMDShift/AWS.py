import boto3
import click

from datetime import datetime, timedelta
from prettytable import PrettyTable
from tqdm import tqdm


DEBUG = True


class AWS_Utils():

    def get_enabled_regions(self, profile=None, role_arn=None):
        client = self.generate_client(resource="ec2", region=None, profile=profile, role_arn=role_arn)
        enabled_regions = [region['RegionName']\
                           for region in client.describe_regions()['Regions']\
                            if region['OptInStatus'] in ["opt-in-not-required", "opted-in"]]
        return enabled_regions


    def generate_client(self, resource, region=None, profile=None, role_arn=None):
        try:
            if region:
                if profile:
                    session_obj = boto3.Session(profile_name=profile, region_name=region)
                elif role_arn:
                    session_obj = self.assume_role(role_arn, region)
                else:
                    session_obj = boto3.Session(region_name=region)
                return session_obj.client(resource)
            else:
                if profile:
                    session_obj = boto3.Session(profile_name=profile)
                elif role_arn:
                    session_obj = self.assume_role(role_arn)
                else:
                    session_obj = boto3.Session()
                return session_obj.client(resource)
        except:
            return None



    def assume_role(self, role_arn, region=None):
        sts = boto3.client("sts")
        assumed_role_obj = sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName="IMDShift"
        )['Credentials']
        
        session = boto3.Session(
            aws_access_key_id=assumed_role_obj['AccessKeyId'],
            aws_secret_access_key=assumed_role_obj['SecretAccessKey'],
            aws_session_token=assumed_role_obj['SessionToken'],
            region_name=region
        ) if region else \
            boto3.Session(
            aws_access_key_id=assumed_role_obj['AccessKeyId'],
            aws_secret_access_key=assumed_role_obj['SecretAccessKey'],
            aws_session_token=assumed_role_obj['SessionToken']
        )
        return session
    
class EC2():
    
    def __init__(self, regions=None, profile=None, role_arn=None) -> None:
        self.regions = regions
        self.aws_utils = AWS_Utils()
        self.ec2 = None
        self.profile = profile
        self.role_arn = role_arn
        self.resource_list = list()
        self.resources_with_imds_v1 = list()
        self.resource_with_metadata_disabled = list()
        self.resources_with_hop_limit_1 = list()
        self.imdsv1_usage_analysis = dict()


    def generate_result(self):
        for region in self.regions:
            self.process_result(region, self.profile, self.role_arn)


    def generate_imdsv1_usage_result(self):
        for region in self.regions:
            self.process_result(region, self.profile, self.role_arn, analyse_resources_flag=False)
            self.analyse_imdsv1_usage(region, self.profile, self.role_arn)

        stats_table = PrettyTable()
        stats_table.align = 'c' 
        stats_table.valign = 'c' 
        stats_table.field_names = ['Region', 'Instances using IMDSv1']

        for region_name in self.imdsv1_usage_analysis:
            stats_table.add_row(
                [
                    region_name,
                    self.imdsv1_usage_analysis[region]
                ]
            )
        
        click.echo(f"[+] Statistics for IMDSv1 usage:")
        click.secho(stats_table.get_string(), bold=True, fg='yellow')

    
    def process_result(self, region, profile=None, role_arn=None, analyse_resources_flag=True):
        self.ec2 = self.aws_utils.generate_client("ec2", region, profile, role_arn)
        instances_details = self.ec2.get_paginator('describe_instances')
        for page in instances_details.paginate():
            for reservation in page['Reservations']:
                self.resource_list.extend(reservation['Instances'])

        if analyse_resources_flag:
            self.analyse_resources()
    

    def analyse_imdsv1_usage(self, region):
        self.imdsv1_usage_analysis[region] = 0
        progress_bar_with_resources = tqdm(self.resource_list, desc=f"[+] Analysing EC2 resources for IMDSv1 usage", colour='green', unit=' resources')
        
        for resource in progress_bar_with_resources:
            cloudwatch_client = self.aws_utils.generate_client('cloudwatch', region=region, profile=self.profile, role_arn=self.role_arn)
            get_metric_data = cloudwatch_client.get_paginator('get_metric_data')

            operation_parameters = {
                "MetricDataQueries": [
                    {
                        'Id': 'imdsv1_migration',
                        'MetricStat': {
                            'Metric': {
                                'Namespace': 'AWS/EC2',
                                'MetricName': 'MetadataNoToken',
                                'Dimensions': [
                                    {
                                    'Name': 'InstanceId',
                                    'Value': resource['InstanceId']
                                    }
                                ]
                            },
                            'Period': 60,
                            'Stat': 'Average',
                        },
                    },
                ],
                "StartTime": datetime.utcnow() - timedelta(days = 30),
                "EndTime": datetime.utcnow()
            }

            response = list()
            for page in get_metric_data.paginate(**operation_parameters):
                response.extend(page['MetricDataResults'][0]['Values'])

            sum_of_data_points_values = sum(response)
    
            if sum_of_data_points_values > 0:
                self.imdsv1_usage_analysis[region] += 1


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
        
    def enable_metadata_for_resources(self, hop_limit=None):
        click.echo(f"[+] Enabling metadata endpoint for EC2 resources for which it is disabled")
        progress_bar_with_resources = tqdm(self.resource_with_metadata_disabled, desc=f"[+] Enabling metadata for EC2 resources", colour='green', unit=' resources')
        for resource in progress_bar_with_resources:
            region = resource['Placement']['AvailabilityZone'][:-1]
            ec2 = self.aws_utils.generate_client("ec2", region=region, profile=self.profile, role_arn=self.role_arn)
            response = ec2.modify_instance_metadata_options(
                InstanceId = resource['InstanceId'],
                HttpTokens = 'required',
                HttpPutResponseHopLimit = hop_limit if hop_limit != None else 2,
                HttpEndpoint = 'enabled',
                HttpProtocolIpv6 = 'disabled',
                InstanceMetadataTags = 'disabled'
            ) 

    # ecs_obj.ecs
    def update_hop_limit_for_resources(self, hop_limit=None):
        click.echo(f"[+] Updating hop limit for EC2 resources with metadata enabled")
        progress_bar_with_resources = tqdm(self.resources_with_hop_limit_1, desc=f"[+] Updating hop limit for EC2 resources to {hop_limit}", colour='green', unit=' resources')
        for resource in progress_bar_with_resources:
            region = resource['Placement']['AvailabilityZone'][:-1]
            ec2 = self.aws_utils.generate_client("ec2", region=region, profile=self.profile, role_arn=self.role_arn)
            response = ec2.modify_instance_metadata_options(
                InstanceId = resource['InstanceId'],
                HttpTokens = 'required',
                HttpPutResponseHopLimit = hop_limit if hop_limit != None else 2,
                HttpEndpoint = 'enabled',
                HttpProtocolIpv6 = 'disabled',
                InstanceMetadataTags = 'disabled'
            )

    # Migrate to imdsv2    
    def migrate_resources(self, hop_limit=None):
        click.echo(f"[+] Performing migration of EC2 resources to IMDSv2")
        progress_bar_with_resources = tqdm(self.resource_list, desc=f"[+] Migrating all EC2 resources to IMDSv2", colour='green', unit=' resources')
        for resource in progress_bar_with_resources:
            if resource not in self.resource_with_metadata_disabled and resource not in  self.resources_with_hop_limit_1:
                region = resource['Placement']['AvailabilityZone'][:-1]
                ec2 = self.aws_utils.generate_client("ec2", region=region, profile=self.profile, role_arn=self.role_arn)
                response = ec2.modify_instance_metadata_options(
                    InstanceId = resource['InstanceId'],
                    HttpTokens = "required",
                    HttpPutResponseHopLimit = hop_limit if hop_limit != None else 2,
                    HttpEndpoint = 'enabled',
                    HttpProtocolIpv6 = 'disabled',
                    InstanceMetadataTags = 'disabled'
                )


class Sagemaker():

    def __init__(self, regions=None, profile=None, role_arn=None) -> None:
        self.regions = regions
        self.aws_utils = AWS_Utils()
        self.sagemaker = None
        self.profile = profile
        self.role_arn = role_arn
        self.resource_list = list()
        self.resources_with_imds_v1 = list()
        self.resource_with_metadata_disabled = list()
        self.resources_with_hop_limit_1 = list()
    
    def generate_result(self):
        for region in self.regions:
            self.process_result(region)
    
    def process_result(self, region):
        try:
            self.sagemaker = self.aws_utils.generate_client("sagemaker", region=region, profile=self.profile, role_arn=self.role_arn)
            instances_details = self.sagemaker.get_paginator('list_notebook_instances')
            for page in instances_details.paginate():
                for instance in page["NotebookInstances"]:
                    name = instance["NotebookInstanceName"]
                    self.resource_list.append((name, region))
            self.analyse_resources()
        except Exception as error:
            click.secho(f'[!] An error occurred while listing Sagemaker resources.', bold=True, fg='red')
            click.secho(f'[!] Error message: {error}.', bold=True, fg='red')

    def analyse_resources(self):

        progress_bar_with_resources = tqdm(self.resource_list, desc=f"[+] Analysing Sagemaker resources", colour='green', unit=' resources')

        for resource in progress_bar_with_resources:
            name = resource[0]
            try:
                imds = self.define_metadataservice(name)
                if imds == "1":
                    self.resources_with_imds_v1.append(resource)
                    
            except Exception as error:
                click.secho(f'[!] An error occurred while analysing Sagemaker resource.', bold=True, fg='red')
                click.secho(f'[!] Error message: {error}.\n', bold=True, fg='red')            


        stats_table = PrettyTable()
        stats_table.align = 'c' 
        stats_table.valign = 'c' 
        stats_table.field_names = ['IMDSv1 Enabled', 'Total Resources']
        stats_table.add_row(
            [
                len(self.resources_with_imds_v1),
                len(self.resource_list)
            ]
        )

        click.echo(f"[+] Statistics from analysis:")
        click.secho(stats_table.get_string(), bold=True, fg='yellow')

    def migrate_resources(self):
        click.echo(f"[+] Performing migration of Sagemaker resources to IMDSv2")
        progress_bar_with_resources = tqdm(self.resources_with_imds_v1, desc=f"[+] Migrating all Sagemaker resources to IMDSv2", colour='green', unit=' resources')
        for resource in progress_bar_with_resources:
            region = resource[1]
            name = resource[0]
            sagemaker = self.aws_utils.generate_client("sagemaker", region=region, profile=self.profile, role_arn=self.role_arn)
            try:
                resource = sagemaker.update_notebook_instance(
                    NotebookInstanceName=name,
                    InstanceMetadataServiceConfiguration={
                            "MinimumInstanceMetadataServiceVersion": '2'
                        }
                    )
            except Exception as error:
                click.secho(f'[!] An error occurred while analysing Sagemaker resource.', bold=True, fg='red')
                click.secho(f'[!] Error message: {error}.\n', bold=True, fg='red')            

    def define_metadataservice(self, name):
        metadata = self.sagemaker.describe_notebook_instance(
            NotebookInstanceName=name
        )["InstanceMetadataServiceConfiguration"]["MinimumInstanceMetadataServiceVersion"]
        return metadata

# Auto Scaling Groups
class ASG():

    def __init__(self, regions=None, ec2_obj=None, profile=None, role_arn=None):
        self.regions = regions
        self.ec2_obj = ec2_obj
        self.aws_utils = AWS_Utils()
        self.ec2 = None
        self.autoscaling = None
        self.profile = profile
        self.role_arn = role_arn    

    def generate_results(self):
        for region in self.regions:
            self.process_result(region)

    def process_result(self, region):
        self.autoscaling = self.aws_utils.generate_client("autoscaling", region=region, profile=self.profile, role_arn=self.role_arn)
        self.ec2 = self.aws_utils.generate_client("ec2", region=region, profile=self.profile, role_arn=self.role_arn)
        instances = self.list_asg_instances()
        instance_data = self.asg_instance_data(instances)
        self.ec2_obj.resource_list = instance_data
        self.ec2_obj.analyse_resources()

    def list_asg_instances(self):
        result = []
        paginator = self.autoscaling.get_paginator('describe_auto_scaling_groups')
        for page in paginator.paginate():
            for as_group in page["AutoScalingGroups"]:
                instances = as_group["Instances"]
                for instance in instances:
                    instance_id = instance['InstanceId']
                    result.append(instance_id)
        return result

    def asg_instance_data(self, instance_ids):
        result = []
        paginator = self.ec2.get_paginator('describe_instances')
        for page in paginator.paginate(InstanceIds=instance_ids):
            for reservation in page['Reservations']:
                result.extend(reservation['Instances'])
        return result


class Lightsail():

    def __init__(self, regions=None, profile=None, role_arn=None) -> None:
        self.regions = regions
        self.aws_utils = AWS_Utils()
        self.lightsail = None
        self.profile = profile
        self.role_arn = role_arn
        self.resource_list = list()
        self.resources_with_imds_v1 = list()
        self.resource_with_metadata_disabled = list()
        self.resources_with_hop_limit_1 = list()
    
    def generate_result(self):
        for region in self.regions:
            self.process_result(region, self.profile, self.role_arn)
    
    def process_result(self, region, profile=None, role_arn=None):
        try:
            self.lightsail = self.aws_utils.generate_client("lightsail", region, profile, role_arn)
            instances_details = self.lightsail.get_paginator('get_instances')
            for page in instances_details.paginate():
                for key in page:
                    if key == 'instances':
                        self.resource_list.extend(page['instances'])

            self.analyse_resources()
        
        except Exception as error:
            click.secho(f'[!] An error occurred while listing Lightsail resources.', bold=True, fg='red')
            click.secho(f'[!] Error message: {error}.', bold=True, fg='red')

    def analyse_resources(self):

        progress_bar_with_resources = tqdm(self.resource_list, desc=f"[+] Analysing Lightsail resources", colour='green', unit=' resources')
        
        for resource in progress_bar_with_resources:

            try:
            
                if resource['metadataOptions']['httpEndpoint'] == 'disabled':
                    self.resource_with_metadata_disabled.append(resource)
                
                if resource['metadataOptions']['httpTokens'] != 'required':
                    self.resources_with_imds_v1.append(resource)
                
                if resource['metadataOptions']['httpPutResponseHopLimit'] == 1:
                    self.resources_with_hop_limit_1.append(resource)

            except KeyError as error:
                click.secho(f'[!] An error occurred while analysing Lightsail resource.', bold=True, fg='red')
                click.secho(f'[!] Error message: {error}.\n', bold=True, fg='red')            


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

        click.echo(f"[+] Statistics from analysis:")
        click.secho(stats_table.get_string(), bold=True, fg='yellow')

    def enable_metadata_for_resources(self, hop_limit=None):
        click.echo(f"[+] Enabling metadata endpoint for Lightsail resources for which it is disabled")
        progress_bar_with_resources = tqdm(self.resource_with_metadata_disabled, desc=f"[+] Enabling metadata for Lightsail resources", colour='green', unit=' resources')
        for resource in progress_bar_with_resources:
            region = resource['location']['regionName']
            lightsail = self.aws_utils.generate_client("lightsail", region=region, profile=self.profile, role_arn=self.role_arn)
            response = lightsail.update_instance_metadata_options(
                instanceName = resource['name'],
                httpTokens = 'required',
                httpPutResponseHopLimit = hop_limit if hop_limit != None else 2,
                httpEndpoint = 'enabled',
                httpProtocolIpv6 = 'disabled',
            ) 

    
    def update_hop_limit_for_resources(self, hop_limit=None):
        click.echo(f"[+] Updating hop limit for Lightsail resources with metadata enabled")
        progress_bar_with_resources = tqdm(self.resources_with_hop_limit_1, desc=f"[+] Updating hop limit for Lightsail resources to {hop_limit}", colour='green', unit=' resources')
        for resource in progress_bar_with_resources:
            region = resource['location']['regionName']
            lightsail = self.aws_utils.generate_client("lightsail", region=region, profile=self.profile, role_arn=self.role_arn)
            response = lightsail.update_instance_metadata_options(
                instanceName = resource['name'],
                httpTokens = 'required',
                httpPutResponseHopLimit = hop_limit if hop_limit != None else 2,
                httpEndpoint = 'enabled',
                httpProtocolIpv6 = 'disabled',
            )


    def migrate_resources(self, hop_limit=None):
        click.echo(f"[+] Performing migration of Lightsail resources to IMDSv2")
        progress_bar_with_resources = tqdm(self.resources_with_imds_v1, desc=f"[+] Migrating all Lightsail resources to IMDSv2", colour='green', unit=' resources')
        for resource in progress_bar_with_resources:
            region = resource['location']['regionName']
            lightsail = self.aws_utils.generate_client("lightsail", region=region, profile=self.profile, role_arn=self.role_arn)
            response = lightsail.update_instance_metadata_options(
                instanceName = resource['name'],
                httpTokens = 'required',
                httpPutResponseHopLimit = hop_limit if hop_limit != None else 2,
                httpEndpoint = 'enabled',
                httpProtocolIpv6 = 'disabled',
            )


# Elastic Container Service
class ECS():

    def __init__(self, regions=None, ec2_obj=None, profile=None, role_arn=None):
        self.regions = regions
        self.ec2_obj = ec2_obj
        self.aws_utils = AWS_Utils()
        self.ec2 = None
        self.ecs = None
        self.profile = profile
        self.role_arn = role_arn

    def process_result(self, region):
        self.ec2 = self.aws_utils.generate_client(resource="ec2", region=region, profile=self.profile, role_arn=self.role_arn)
        self.ecs = self.aws_utils.generate_client(resource="ecs", region=region, profile=self.profile, role_arn=self.role_arn)
        clusters = self.list_clusters()
        instance_data = self.container_instance_data(clusters)
        self.ec2_obj.resource_list = instance_data
        self.ec2_obj.analyse_resources()

    def generate_results(self):
        for region in self.regions:
            self.process_result(region)

    def list_clusters(self):
        result = []
        paginator = self.ecs.get_paginator('list_clusters')
        for page in paginator.paginate():
            result.extend(page['clusterArns'])
        return result

    def container_instance_data(self, clusters):
        result = []
        for cluster in clusters:
            paginator = self.ecs.get_paginator('list_container_instances')
            for page in paginator.paginate(cluster=cluster):
                container_instance_arns = page['containerInstanceArns']
                if container_instance_arns:
                    describe_instances = self.ecs.describe_container_instances(cluster=cluster, containerInstances=container_instance_arns)['containerInstances']
                    instance_ids = [instance['ec2InstanceId'] for instance in describe_instances]
                    instance_details = self.ec2.describe_instances(InstanceIds=instance_ids)['Reservations']
                    for reservation in instance_details:
                        result.extend(reservation['Instances'])
        return result

# Elastic Kubernetes Service
class EKS():

    def __init__(self, regions=None, ec2_obj=None, profile=None, role_arn=None):
        self.regions = regions
        self.ec2_obj = ec2_obj
        self.aws_utils = AWS_Utils()
        self.ec2 = None
        self.eks = None
        self.autoscaling = None
        self.profile = profile
        self.role_arn = role_arn

    def generate_results(self):
        for region in self.regions:
            self.process_result(region)
    
    def process_result(self, region):
        self.eks = self.aws_utils.generate_client(resource="eks", region=region, profile=self.profile, role_arn=self.role_arn)
        self.ec2 = self.aws_utils.generate_client(resource="ec2", region=region, profile=self.profile, role_arn=self.role_arn)
        self.autoscaling = self.aws_utils.generate_client("autoscaling", region)
        clusters = self.list_clusters()
        instance_data = self.eks_nodegroups(clusters)
        self.ec2_obj.resource_list = instance_data
        self.ec2_obj.analyse_resources()

    def list_clusters(self):
        result = []
        paginator = self.eks.get_paginator('list_clusters')
        for page in paginator.paginate():
            result.extend(page['clusters'])
        return result

    def eks_nodegroups(self, clusters):
        instance_ids = []
        for cluster in clusters:
            paginator = self.eks.get_paginator('list_nodegroups')
            for page in paginator.paginate(clusterName=cluster):
                for node_group_name in page['nodegroups']:
                    node_group_details = self.eks.describe_nodegroup(clusterName=cluster, nodegroupName=node_group_name)
                    auto_scaling_groups = node_group_details["nodegroup"]["resources"]["autoScalingGroups"]
                    for asg in auto_scaling_groups:
                        asg_details = self.autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=[asg["name"]])["AutoScalingGroups"][0]["Instances"]
                        instance_ids.extend([instance["InstanceId"] for instance in asg_details])
        instance_data = self.process_instancedata(instance_ids)
        return instance_data

    def process_instancedata(self, instance_ids):
        result = []
        paginator = self.ec2.get_paginator('describe_instances')
        for page in paginator.paginate(InstanceIds=instance_ids):
            for reservation in page['Reservations']:
                result.extend(reservation['Instances'])
        return result

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
    lightsail_obj = Lightsail()
