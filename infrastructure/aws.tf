terraform {
  backend "s3" {
    bucket = "cddo-sgs-sandbox-tfstate"
    key    = "dinum-hackdays-2025-scratch.tfstate"
    region = "eu-west-2"
  }
}

provider "aws" {
  region = "eu-west-2"

  default_tags {
    tags = {
      "Reference" : "https://github.com/alphagov/dinum-hackdays-2025-scratch",
      "Environment" : "Test"
    }
  }
}
