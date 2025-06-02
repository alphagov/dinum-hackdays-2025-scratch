import traceback
import json
from apig_wsgi import make_lambda_handler
from app import app


def lambda_handler(event, context):
    """
    Set up the Lambda handler. This takes the request from the Internet and does something valuable with it, routing it
    according to the URL. This will map onto one of the routes in the Flask app

    :param event:
    :param context:
    :return:
    """
    alb_lambda_handler = make_lambda_handler(app)
    try:
        response = alb_lambda_handler(event, context)
        print(
            json.dumps(
                {
                    "Request": event,
                    "Response": {
                        "statusCode": response["statusCode"],
                        "headers": response["headers"],
                        "body_length": len(response["body"]),
                    },
                },
                default=str,
            )
        )
        return response
    except Exception as e:
        print(
            json.dumps(
                {"Request": event, "Response": None, "Error": traceback.format_exc()},
                default=str,
            )
        )
        return {"statusCode": 500, "body": "Error"}
