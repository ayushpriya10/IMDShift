#! /usr/bin/python3

import boto3

sg = boto3.client("sagemaker")

def main():
    instance_details = sg.get_paginator("list_notebook_instances")
    for page in instance_details.paginate():
        for instance in page["NotebookInstances"]:
            name = instance["NotebookInstanceName"]
            imds_version = define_instance(name)
            instance_type = instance["InstanceType"]
            print(f"[+]Instance: {name}\n[+]IMDS: {imds_version}")
            
def define_instance(name):
    metadata = sg.describe_notebook_instance(
        NotebookInstanceName=name
    )['InstanceMetadataServiceConfiguration']['MinimumInstanceMetadataServiceVersion']
    return metadata

if __name__ == "__main__":
    main()