#!/usr/bin/env python
from constructs import Construct
from cdktf import App, TerraformStack
from infra.network_stack import NetworkStack
from infra.infra_stack import InfraStack
from apps.service_stack import ServiceStack

ENV = "dev"
AWS_REGION = "us-east-1"
BACKEND_S3_BUCKET = "blog.abdelfare.me"
BACKEND_S3_KEY = f"{ENV}/cdktf-samples"
CLUSTER_NAME = "cdktf-samples"


class MyStack(TerraformStack):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)


app = App()
MyStack(app, "aws-cdktf-samples-fargate")

network = NetworkStack(
    app,
    "network",
    {
        "region": AWS_REGION,
        "backend_bucket": BACKEND_S3_BUCKET,
        "backend_key_prefix": BACKEND_S3_KEY,
    },
)

infra = InfraStack(
    app,
    "infra",
    {
        "vpc_id": network.vpc_id,
        "public_subnets": network.public_subnets,
    },
    {
        "region": AWS_REGION,
        "backend_bucket": BACKEND_S3_BUCKET,
        "backend_key_prefix": BACKEND_S3_KEY,
        "cluster_name": CLUSTER_NAME,
    },
)

java_api = ServiceStack(
    app,
    "java_api",
    {
        "vpc_id": network.vpc_id,
        "private_subnets": network.private_subnets,
    },
    {
        "alb_sg": infra.alb_sg,
        "alb_listener": infra.alb_listener,
        "cluster_id": infra.cluster_id,
    },
    {
        "region": AWS_REGION,
        "backend_bucket": BACKEND_S3_BUCKET,
        "backend_key_prefix": BACKEND_S3_KEY,
        "app_name": "java-api",
        "app_port": 8080,
        "desired_count": 1,
    },
)

app.synth()
