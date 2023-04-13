#! /usr/bin/python3

import boto3

# List ECS Clusters
def list_ecs_clusters(ecs):
    result = []
    marker = None
    while True:
        if marker:
            clusters = ecs.list_clusters(
                nextToken=marker
            )
            arns = clusters["clusterArns"]
            for cluster in arns:
                #print(f"[+]Cluster: {cluster}")
                result.append(cluster)
        else:
            clusters = ecs.list_clusters()
            arns = clusters["clusterArns"]
            for cluster in arns:
                #print(f"[+]Cluster without nextToken: {cluster}")
                result.append(cluster)
        
        if "nextToken" in clusters:
            marker = clusters["nextToken"]
        else:
            return result

def container_instances(clusters):
    instances = [ecs.list_container_instances(Cluster=cluster)["containerInstanceArns"] for cluster in clusters]
    
    for cluster in clusters:
        instances = ecs.list_container_instances(Cluster=cluster)["containerInstanceArns"]
        

if __name__ == "__main__":
    ecs = boto3.client("ecs")
