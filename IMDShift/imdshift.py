import click
import sys


from .utilities import trigger_scan, validate_services, ScanRegion, validate_regions
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

@click.option('--services', type=str, default=None, help='This flag specifies services scan for IMDSv1 usage from [EC2, Sagemaker, ASG (Auto Scaling Groups), Lightsail, ECS, EKS, Beanstalk]. Format: "--services EC2,Sagemaker,ASG"')
@click.option('--include-regions', type=str, default='ALL', help='This flag specifies regions explicitly to include scan for IMDSv1 usage. Format: "--include-regions ap-south-1,ap-southeast-1"')
@click.option('--exclude-regions', type=str, default=None, help='This flag specifies regions to exclude from the scan explicitly. Format: "--exclude-regions ap-south-1,ap-southeast-1"')
@click.option('--migrate', is_flag=True, default=False, help='This boolean flag enables IMDShift to perform the migration, defaults to "False". Format: "--migrate"')
@click.option('--update-hop-limit', type=int, default=None, help='This flag specifies if the hop limit should be updated and with what value. It is recommended to set the hop limit to "2" to enable containers to be able to work with the IMDS endpoint. If this flag is not passed, hop limit is not updated during migration. Format: "--update-hop-limit 3"')
@click.option('--enable-imds', is_flag=True, default=False, help='This boolean flag enables IMDShift to enable the metadata endpoint for resources that have it disabled and then perform the migration, defaults to "False". Format: "--enable-imds"')

def cli_handler(services, include_regions, exclude_regions, migrate, update_hop_limit, enable_imds):
    if services == None:
        click.secho('[!] No services specified to scan. Exiting.', bold=True, fg='red')

    else:
        services = [service.strip() for service in services.split(',')]
        regions = ScanRegion(included_regions=include_regions, excluded_regions=exclude_regions).result()
        click.echo(f"[+] Scanning specified services: {', '.join(services)}")
        click.echo(f"[+] Scanning Region: {regions}")
        validate_services(services)
        trigger_scan(services=services,regions=regions, migrate=migrate, update_hop_limit=update_hop_limit, enable_imds=enable_imds)