import click
import sys


from .utilities import trigger_scan, validate_services, ScanRegion, print_policies, check_imdsv1_usage

CLI_PROMPT = """
 /$$$$$$ /$$      /$$ /$$$$$$$   /$$$$$$  /$$       /$$  /$$$$$$   /$$    
|_  $$_/| $$$    /$$$| $$__  $$ /$$__  $$| $$      |__/ /$$__  $$ | $$    
  | $$  | $$$$  /$$$$| $$  \ $$| $$  \__/| $$$$$$$  /$$| $$  \__//$$$$$$  
  | $$  | $$ $$/$$ $$| $$  | $$|  $$$$$$ | $$__  $$| $$| $$$$   |_  $$_/  
  | $$  | $$  $$$| $$| $$  | $$ \____  $$| $$  \ $$| $$| $$_/     | $$    
  | $$  | $$\  $ | $$| $$  | $$ /$$  \ $$| $$  | $$| $$| $$       | $$ /$$
 /$$$$$$| $$ \/  | $$| $$$$$$$/|  $$$$$$/| $$  | $$| $$| $$       |  $$$$/
|______/|__/     |__/|_______/  \______/ |__/  |__/|__/|__/        \___/  
"""

# click.secho(CLI_PROMPT, blink=True, bold=True, fg='cyan')
click.secho(CLI_PROMPT, bold=True, fg='cyan')


@click.command()

@click.option('--services', type=str, default=None, help='This flag specifies services to scan for IMDSv1 usage from [EC2, Sagemaker, ASG (Auto Scaling Groups), Lightsail, ECS, EKS, Beanstalk]. Format: "--services EC2,Sagemaker,ASG"')
@click.option('--include-regions', type=str, default='ALL', help='This flag specifies regions explicitly to include scan for IMDSv1 usage. Format: "--include-regions ap-south-1,ap-southeast-1"')
@click.option('--exclude-regions', type=str, default=None, help='This flag specifies regions to exclude from the scan explicitly. Format: "--exclude-regions ap-south-1,ap-southeast-1"')
@click.option('--migrate', is_flag=True, default=False, help='This boolean flag enables IMDShift to perform the migration, defaults to "False". Format: "--migrate"')
@click.option('--update-hop-limit', type=int, default=None, help='This flag specifies if the hop limit should be updated and with what value. It is recommended to set the hop limit to "2" to enable containers to be able to work with the IMDS endpoint. If this flag is not passed, hop limit is not updated during migration. Format: "--update-hop-limit 3"')
@click.option('--enable-imds', is_flag=True, default=False, help='This boolean flag enables IMDShift to enable the metadata endpoint for resources that have it disabled and then perform the migration, defaults to "False". Format: "--enable-imds"')
@click.option('--profile', type=str, default=None, help='This allows you to use any profile from your ~/.aws/credentials file. Format: "--profile prod-env"')
@click.option('--role-arn', type=str, default=None, help='This flag let\'s you assume a role via aws sts. Format: "--role-arn arn:aws:sts::111111111:role/John"')
@click.option('--print-scps', is_flag=True, default=False, help='This boolean flag prints Service Control Policies (SCPs) that can be used to control IMDS usage, like deny access for credentials fetched from IMDSv2 or deny creation of resources with IMDSv1, defaults to "False". Format: "--print-scps"')
@click.option('--check-imds-usage', is_flag=True, default=False, help='This boolean flag launches a scan to identify how many instances are using IMDSv1 in specified regions, during the last 30 days, by using the "MetadataNoToken" CloudWatch metric, defaults to "False". Format: "--check-imds-usage"')
def cli_handler(services, include_regions, exclude_regions, migrate, update_hop_limit, enable_imds, profile, role_arn, print_scps, check_imds_usage):
    if print_scps:
        print_policies()


    if check_imds_usage:
        regions = ScanRegion(included_regions=include_regions, excluded_regions=exclude_regions, profile=profile, role_arn=role_arn).result()
        click.echo(f"[+] Analysing IMDSv1 usage, in the last 30 days, with 'MetadataNoToken' CloudWatch metric.")
        click.echo(f"[+] Scanning Regions: {', '.join(regions)}")

        check_imdsv1_usage(regions=regions, profile=profile, role_arn=role_arn)


    if services == None:
        click.secho('[!] No services specified to scan. Exiting.', bold=True, fg='red')

    else:
        services = [service.strip().upper() for service in services.split(',')]
        regions = ScanRegion(included_regions=include_regions, excluded_regions=exclude_regions, profile=profile, role_arn=role_arn).result()
        click.echo(f"[+] Scanning specified services: {', '.join(services)}")
        click.echo(f"[+] Scanning Regions: {', '.join(regions)}")
        validate_services(services)
        trigger_scan(services=services,regions=regions, migrate=migrate, update_hop_limit=update_hop_limit, enable_imds=enable_imds, profile=profile, role_arn=role_arn)