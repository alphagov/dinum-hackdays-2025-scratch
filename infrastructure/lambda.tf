resource "aws_lambda_function_url" "wsgi_latest" {
  function_name      = aws_lambda_function.lambda.function_name
  authorization_type = "NONE"
}

resource "aws_lambda_function_url" "wsgi_latest_dsfr" {
  function_name      = aws_lambda_function.lambda_dsfr.function_name
  authorization_type = "NONE"
}

resource "random_string" "flask_secret_key" {
  length  = 32
  special = false
  upper   = false

  lifecycle {
    ignore_changes = [
      special,
      upper,
    ]
  }
}

locals {
  flask_secret_key = sensitive(random_string.flask_secret_key.result)
}

variable "CLIENT_ID" {
  type      = string
  sensitive = true
}

variable "CLIENT_SECRET" {
  type      = string
  sensitive = true
}

variable "GRIST_API_KEY" {
  type      = string
  sensitive = true
}

variable "GRIST_SERVER" {
  type    = string
  default = "https://baller-hackdays-2025.getgrist.com"
}

variable "GRIST_DOCUMENT_ID" {
  type      = string
  sensitive = true
}

resource "aws_lambda_function" "lambda" {
  filename         = "../flask-app/GovGroupsLambda.zip"
  source_code_hash = filebase64sha256("../flask-app/GovGroupsLambda.zip")

  description   = "GovGroups Lambda WSGI"
  function_name = "GovGroupsLambdaFunction"
  role          = aws_iam_role.lambda_role.arn
  handler       = "wsgi.lambda_handler"
  runtime       = "python3.12"

  publish = true

  memory_size = 512
  timeout     = 60

  lifecycle {
    ignore_changes = [
    ]
  }

  environment {
    variables = {
      SECRET_KEY        = local.flask_secret_key
      CLIENT_ID         = var.CLIENT_ID
      CLIENT_SECRET     = var.CLIENT_SECRET
      GRIST_API_KEY     = var.GRIST_API_KEY
      GRIST_SERVER      = var.GRIST_SERVER
      GRIST_DOCUMENT_ID = var.GRIST_DOCUMENT_ID
      OPENID_CONFIG_URL = "https://sso.service.security.gov.uk/.well-known/openid-configuration"
      DESIGN_TYPE       = "govuk"
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_pa,
    aws_cloudwatch_log_group.lambda_lg,
  ]
}

resource "aws_lambda_function" "lambda_dsfr" {
  filename         = "../flask-app/GovGroupsLambda.zip"
  source_code_hash = filebase64sha256("../flask-app/GovGroupsLambda.zip")

  description   = "GovGroups Lambda WSGI - DSFR"
  function_name = "GovGroupsLambdaFunctionDSFR"
  role          = aws_iam_role.lambda_role.arn
  handler       = "wsgi.lambda_handler"
  runtime       = "python3.12"

  publish = true

  memory_size = 512
  timeout     = 60

  lifecycle {
    ignore_changes = [
    ]
  }

  environment {
    variables = {
      SECRET_KEY        = local.flask_secret_key
      CLIENT_ID         = var.CLIENT_ID
      CLIENT_SECRET     = var.CLIENT_SECRET
      GRIST_API_KEY     = var.GRIST_API_KEY
      GRIST_SERVER      = var.GRIST_SERVER
      GRIST_DOCUMENT_ID = var.GRIST_DOCUMENT_ID
      OPENID_CONFIG_URL = "https://sso.service.security.gov.uk/.well-known/openid-configuration"
      DESIGN_TYPE       = "dsfr"
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_pa,
    aws_cloudwatch_log_group.lambda_lg,
  ]
}

resource "aws_iam_role" "lambda_role" {
  name               = "GovGroupsLambdaRole"
  assume_role_policy = data.aws_iam_policy_document.arpd.json
}

resource "aws_cloudwatch_log_group" "lambda_lg" {
  name              = "/aws/lambda/GovGroupsLambdaFunction"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "lambda_lg_dsfr" {
  name              = "/aws/lambda/GovGroupsLambdaFunctionDSFR"
  retention_in_days = 14
}

# See also the following AWS managed policy: AWSLambdaBasicExecutionRole
resource "aws_iam_policy" "lambda_policy" {
  name        = "GovGroupsLambdaPolicy"
  path        = "/"
  description = "IAM policy for logging from a lambda"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:*:*:*"
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_pa" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

data "aws_iam_policy_document" "arpd" {
  statement {
    sid    = "AllowAwsToAssumeRole"
    effect = "Allow"

    actions = ["sts:AssumeRole"]

    principals {
      type = "Service"

      identifiers = [
        "lambda.amazonaws.com",
      ]
    }
  }
}
