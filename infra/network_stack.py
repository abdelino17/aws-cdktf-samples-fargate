from constructs import Construct
from cdktf import S3Backend, TerraformStack
from cdktf_cdktf_provider_aws.provider import AwsProvider
from cdktf_cdktf_provider_aws.vpc import Vpc
from cdktf_cdktf_provider_aws.subnet import Subnet
from cdktf_cdktf_provider_aws.eip import Eip
from cdktf_cdktf_provider_aws.nat_gateway import NatGateway
from cdktf_cdktf_provider_aws.route import Route
from cdktf_cdktf_provider_aws.route_table import RouteTable
from cdktf_cdktf_provider_aws.route_table_association import RouteTableAssociation
from cdktf_cdktf_provider_aws.internet_gateway import InternetGateway


class NetworkStack(TerraformStack):
    def __init__(self, scope: Construct, ns: str, params: dict):
        super().__init__(scope, ns)

        self.region = params["region"]

        # configure the AWS provider to use the us-east-1 region
        AwsProvider(self, "AWS", region=self.region)

        # use S3 as backend
        S3Backend(
            self,
            bucket=params["backend_bucket"],
            key=params["backend_key_prefix"] + "/network.tfstate",
            region=self.region,
        )

        # create the vpc
        vpc_demo = Vpc(self, "vpc-demo", cidr_block="192.168.0.0/16")

        # create two public subnets
        public_subnet1 = Subnet(
            self,
            "public-subnet-1",
            vpc_id=vpc_demo.id,
            availability_zone=f"{self.region}a",
            cidr_block="192.168.1.0/24",
        )

        public_subnet2 = Subnet(
            self,
            "public-subnet-2",
            vpc_id=vpc_demo.id,
            availability_zone=f"{self.region}b",
            cidr_block="192.168.2.0/24",
        )

        # create. the internet gateway
        igw = InternetGateway(self, "igw", vpc_id=vpc_demo.id)

        # create the public route table
        public_rt = Route(
            self,
            "public-rt",
            route_table_id=vpc_demo.main_route_table_id,
            destination_cidr_block="0.0.0.0/0",
            gateway_id=igw.id,
        )

        # create the private subnets
        private_subnet1 = Subnet(
            self,
            "private-subnet-1",
            vpc_id=vpc_demo.id,
            availability_zone=f"{self.region}a",
            cidr_block="192.168.10.0/24",
        )

        private_subnet2 = Subnet(
            self,
            "private-subnet-2",
            vpc_id=vpc_demo.id,
            availability_zone=f"{self.region}b",
            cidr_block="192.168.20.0/24",
        )

        # create the Elastic IPs
        eip1 = Eip(self, "nat-eip-1", depends_on=[igw])
        eip2 = Eip(self, "nat-eip-2", depends_on=[igw])

        # create the NAT Gateways
        private_nat_gw1 = NatGateway(
            self,
            "private-nat-1",
            subnet_id=public_subnet1.id,
            allocation_id=eip1.id,
        )

        private_nat_gw2 = NatGateway(
            self,
            "private-nat-2",
            subnet_id=public_subnet2.id,
            allocation_id=eip2.id,
        )

        # create Route Tables
        private_rt1 = RouteTable(self, "private-rt1", vpc_id=vpc_demo.id)
        private_rt2 = RouteTable(self, "private-rt2", vpc_id=vpc_demo.id)

        # add default routes to tables
        Route(
            self,
            "private-rt1-default-route",
            route_table_id=private_rt1.id,
            destination_cidr_block="0.0.0.0/0",
            nat_gateway_id=private_nat_gw1.id,
        )

        Route(
            self,
            "private-rt2-default-route",
            route_table_id=private_rt2.id,
            destination_cidr_block="0.0.0.0/0",
            nat_gateway_id=private_nat_gw2.id,
        )

        # associate routes with subnets
        RouteTableAssociation(
            self,
            "public-rt-association",
            subnet_id=private_subnet2.id,
            route_table_id=private_rt2.id,
        )

        RouteTableAssociation(
            self,
            "private-rt1-association",
            subnet_id=private_subnet1.id,
            route_table_id=private_rt1.id,
        )

        RouteTableAssociation(
            self,
            "private-rt2-association",
            subnet_id=private_subnet2.id,
            route_table_id=private_rt2.id,
        )

        # terraform outputs
        self.vpc_id = vpc_demo.id
        self.public_subnets = [public_subnet1.id, public_subnet2.id]
        self.private_subnets = [private_subnet1.id, private_subnet2.id]
