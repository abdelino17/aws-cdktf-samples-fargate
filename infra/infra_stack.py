from constructs import Construct
from cdktf import S3Backend, TerraformStack, TerraformOutput
from cdktf_cdktf_provider_aws.provider import AwsProvider
from cdktf_cdktf_provider_aws.ecs_cluster import EcsCluster
from cdktf_cdktf_provider_aws.lb import Lb
from cdktf_cdktf_provider_aws.lb_listener import (
    LbListener,
    LbListenerDefaultAction,
    LbListenerDefaultActionFixedResponse,
)
from cdktf_cdktf_provider_aws.security_group import (
    SecurityGroup,
    SecurityGroupIngress,
    SecurityGroupEgress,
)


class InfraStack(TerraformStack):
    def __init__(self, scope: Construct, ns: str, network: dict, params: dict):
        super().__init__(scope, ns)

        self.region = params["region"]

        # Configure the AWS provider to use the us-east-1 region
        AwsProvider(self, "AWS", region=self.region)

        # use S3 as backend
        S3Backend(
            self,
            bucket=params["backend_bucket"],
            key=params["backend_key_prefix"] + "/infra.tfstate",
            region=self.region,
        )

        # create the ALB security group
        alb_sg = SecurityGroup(
            self,
            "alb-sg",
            vpc_id=network["vpc_id"],
            ingress=[
                SecurityGroupIngress(
                    protocol="tcp", from_port=80, to_port=80, cidr_blocks=["0.0.0.0/0"]
                )
            ],
            egress=[
                SecurityGroupEgress(
                    protocol="-1", from_port=0, to_port=0, cidr_blocks=["0.0.0.0/0"]
                )
            ],
        )

        # create the ALB
        alb = Lb(
            self,
            "alb",
            internal=False,
            load_balancer_type="application",
            security_groups=[alb_sg.id],
            subnets=network["public_subnets"],
        )

        # create the LB Listener
        alb_listener = LbListener(
            self,
            "alb-listener",
            load_balancer_arn=alb.arn,
            port=80,
            protocol="HTTP",
            default_action=[
                LbListenerDefaultAction(
                    type="fixed-response",
                    fixed_response=LbListenerDefaultActionFixedResponse(
                        content_type="text/plain",
                        status_code="404",
                        message_body="Could not find the resource you are looking for",
                    ),
                )
            ],
        )

        # create the ECS cluster
        cluster = EcsCluster(self, "cluster", name=params["cluster_name"])

        self.alb_arn = alb.arn
        self.alb_listener = alb_listener.arn
        self.alb_sg = alb_sg.id
        self.cluster_id = cluster.id

        TerraformOutput(self, "alb_dns", value=alb.dns_name)
