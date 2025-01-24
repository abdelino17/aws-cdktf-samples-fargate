# AWS CDKTF Fargate

![cdktf](https://img.shields.io/badge/cdktf-0.20.8-informational)
![Twitter Follow](https://img.shields.io/twitter/follow/abdelFare?logoColor=lime&style=social)

This repository contains the infrastructure code described in this [article](https://blog.abdelfare.me/post/deploy-springboot-on-aws-ecs-using-cdktf).

## Usage

1. Install the cdktkf cli `npm i -g cdktf-cli@latest`
2. Clone this Repo `git clone https://github.com/abdelino17/aws-cdktf-samples-fargate`
3. Navigate to the new folder `cd aws-cdktf-samples-fargate`
4. Update the
5. Create the virtualenv with [pipenv](https://pipenv.pypa.io/en/latest/) and install the required packages `PIPENV_VENV_IN_PROJECT=1 pipenv install`
6. Generate the terraform state of your project with the command `cdktf synth`
7. Deploy your stack `cdktf deploy`
