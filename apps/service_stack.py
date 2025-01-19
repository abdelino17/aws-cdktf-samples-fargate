from constructs import Construct
import json
from cdktf import S3Backend, TerraformStack, Token, TerraformOutput
from cdktf_cdktf_provider_aws.provider import AwsProvider
from cdktf_cdktf_provider_aws.ecs_service import (
    EcsService,
    EcsServiceLoadBalancer,
    EcsServiceNetworkConfiguration,
)
from cdktf_cdktf_provider_aws.ecr_repository import (
    EcrRepository,
    EcrRepositoryImageScanningConfiguration,
)
from cdktf_cdktf_provider_aws.ecr_lifecycle_policy import EcrLifecyclePolicy
from cdktf_cdktf_provider_aws.ecs_task_definition import (
    EcsTaskDefinition,
)
from cdktf_cdktf_provider_aws.lb_listener_rule import (
    LbListenerRule,
    LbListenerRuleAction,
    LbListenerRuleCondition,
    LbListenerRuleConditionPathPattern,
)
from cdktf_cdktf_provider_aws.lb_target_group import (
    LbTargetGroup,
    LbTargetGroupHealthCheck,
)
from cdktf_cdktf_provider_aws.security_group import (
    SecurityGroup,
    SecurityGroupIngress,
    SecurityGroupEgress,
)
from cdktf_cdktf_provider_aws.cloudwatch_log_group import CloudwatchLogGroup
from cdktf_cdktf_provider_aws.data_aws_iam_policy_document import (
    DataAwsIamPolicyDocument,
)
from cdktf_cdktf_provider_aws.iam_role import IamRole
from cdktf_cdktf_provider_aws.iam_role_policy_attachment import IamRolePolicyAttachment


class ServiceStack(TerraformStack):
    def __init__(
        self, scope: Construct, ns: str, network: dict, infra: dict, params: dict
    ):
        super().__init__(scope, ns)

        self.region = params["region"]

        # Configure the AWS provider to use the us-east-1 region
        AwsProvider(self, "AWS", region=self.region)

        # use S3 as backend
        S3Backend(
            self,
            bucket=params["backend_bucket"],
            key=params["backend_key_prefix"] + "/" + params["app_name"] + ".tfstate",
            region=self.region,
        )

        # create the service security group
        svc_sg = SecurityGroup(
            self,
            "svc-sg",
            vpc_id=network["vpc_id"],
            ingress=[
                SecurityGroupIngress(
                    protocol="tcp",
                    from_port=params["app_port"],
                    to_port=params["app_port"],
                    security_groups=[infra["alb_sg"]],
                )
            ],
            egress=[
                SecurityGroupEgress(
                    protocol="-1", from_port=0, to_port=0, cidr_blocks=["0.0.0.0/0"]
                )
            ],
        )

        # create the service target group
        svc_tg = LbTargetGroup(
            self,
            "svc-target-group",
            name="svc-tg",
            port=params["app_port"],
            protocol="HTTP",
            vpc_id=network["vpc_id"],
            target_type="ip",
            health_check=LbTargetGroupHealthCheck(path="/ping", matcher="200"),
        )

        # create the service listener rule
        LbListenerRule(
            self,
            "alb-rule",
            listener_arn=infra["alb_listener"],
            action=[LbListenerRuleAction(type="forward", target_group_arn=svc_tg.arn)],
            condition=[
                LbListenerRuleCondition(
                    path_pattern=LbListenerRuleConditionPathPattern(values=["/*"])
                )
            ],
        )

        # create the ECR repository
        repo = EcrRepository(
            self,
            params["app_name"],
            image_scanning_configuration=EcrRepositoryImageScanningConfiguration(
                scan_on_push=True
            ),
            image_tag_mutability="MUTABLE",
            name=params["app_name"],
        )

        EcrLifecyclePolicy(
            self,
            "this",
            repository=repo.name,
            policy=json.dumps(
                {
                    "rules": [
                        {
                            "rulePriority": 1,
                            "description": "Keep last 10 images",
                            "selection": {
                                "tagStatus": "tagged",
                                "tagPrefixList": ["v"],
                                "countType": "imageCountMoreThan",
                                "countNumber": 10,
                            },
                            "action": {"type": "expire"},
                        },
                        {
                            "rulePriority": 2,
                            "description": "Expire images older than 3 days",
                            "selection": {
                                "tagStatus": "untagged",
                                "countType": "sinceImagePushed",
                                "countUnit": "days",
                                "countNumber": 3,
                            },
                            "action": {"type": "expire"},
                        },
                    ]
                }
            ),
        )

        # create the service log group
        service_log_group = CloudwatchLogGroup(
            self,
            "svc_log_group",
            name=params["app_name"],
            retention_in_days=1,
        )

        ecs_assume_role = DataAwsIamPolicyDocument(
            self,
            "assume_role",
            statement=[
                {
                    "actions": ["sts:AssumeRole"],
                    "principals": [
                        {
                            "identifiers": ["ecs-tasks.amazonaws.com"],
                            "type": "Service",
                        },
                    ],
                },
            ],
        )

        # create the service execution role
        service_execution_role = IamRole(
            self,
            "service_execution_role",
            assume_role_policy=ecs_assume_role.json,
            name=params["app_name"] + "-exec-role",
        )

        IamRolePolicyAttachment(
            self,
            "ecs_role_policy",
            policy_arn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy",
            role=service_execution_role.name,
        )

        # create the service task role
        service_task_role = IamRole(
            self,
            "service_task_role",
            assume_role_policy=ecs_assume_role.json,
            name=params["app_name"] + "-task-role",
        )

        # create the service task definition
        task = EcsTaskDefinition(
            self,
            "svc-task",
            family="service",
            network_mode="awsvpc",
            requires_compatibilities=["FARGATE"],
            cpu="256",
            memory="512",
            task_role_arn=service_task_role.arn,
            execution_role_arn=service_execution_role.arn,
            container_definitions=json.dumps(
                [
                    {
                        "name": "svc",
                        "image": f"{repo.repository_url}:latest",
                        "networkMode": "awsvpc",
                        "healthCheck": {
                            "Command": ["CMD-SHELL", "echo hello"],
                            "Interval": 5,
                            "Timeout": 2,
                            "Retries": 3,
                        },
                        "portMappings": [
                            {
                                "containerPort": params["app_port"],
                                "hostPort": params["app_port"],
                            }
                        ],
                        "logConfiguration": {
                            "logDriver": "awslogs",
                            "options": {
                                "awslogs-group": service_log_group.name,
                                "awslogs-region": params["region"],
                                "awslogs-stream-prefix": params["app_name"],
                            },
                        },
                    }
                ]
            ),
        )

        # create the ECS service
        EcsService(
            self,
            "ecs_service",
            name=params["app_name"] + "-service",
            cluster=infra["cluster_id"],
            task_definition=task.arn,
            desired_count=params["desired_count"],
            launch_type="FARGATE",
            force_new_deployment=True,
            network_configuration=EcsServiceNetworkConfiguration(
                subnets=network["private_subnets"],
                security_groups=[svc_sg.id],
            ),
            load_balancer=[
                EcsServiceLoadBalancer(
                    target_group_arn=svc_tg.id,
                    container_name="svc",
                    container_port=params["app_port"],
                )
            ],
        )

        TerraformOutput(
            self,
            "ecr_repository_url",
            description="url of the ecr repo",
            value=repo.repository_url,
        )
