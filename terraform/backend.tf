terraform {
  required_version = ">= 1.6.0"
  backend "s3" {
    bucket         = "tfstate-lightscore-eun1"
    key            = "envs/prod/terraform.tfstate"
    region         = "eu-north-1"
    dynamodb_table = "tf-locks-lightscore-eun1"
    encrypt        = true
  }
}