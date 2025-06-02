#!/usr/bin/env python3

import os
from flask import Flask, redirect, url_for, session, render_template
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from auth_helpers import RequireUser, UserOptional
from grist_api import GristDocAPI

load_dotenv()  # take environment variables

app = Flask(__name__, template_folder="templates", static_folder="assets")
app.secret_key = os.getenv("SECRET_KEY", os.urandom(24))

CLIENT_ID = os.getenv("CLIENT_ID")

GRIST_DOC_ID = os.getenv("GRIST_DOCUMENT_ID")
GRIST_SERVER = os.getenv("GRIST_SERVER")

grist = GristDocAPI(GRIST_DOC_ID, server=GRIST_SERVER)

oauth = OAuth(app)
oauth.register(
    name="internal_access",
    server_metadata_url="https://sso.service.security.gov.uk/.well-known/openid-configuration",
    client_id=CLIENT_ID,
    client_secret=os.getenv("CLIENT_SECRET"),
    client_kwargs={"scope": "openid profile email"},
)


@app.route("/")
@RequireUser
def route_root():
    return render_template(
        "root.html",
        user=session.get("user", {}),
        navigation=[
            {"label": "Home", "url": url_for("route_root"), "active": True},
            {"label": "Logout", "url": url_for("route_logout")},
        ],
    )


@app.route("/login")
def route_login():
    redirect_uri = url_for("route_auth", _external=True)
    session["nonce"] = os.urandom(16).hex()
    return oauth.internal_access.authorize_redirect(
        redirect_uri, nonce=session["nonce"]
    )


@app.route("/logout")
def route_logout():
    session.pop("user", None)
    return redirect(
        f"https://sso.service.security.gov.uk/sign-out?from_app={CLIENT_ID}"
    )


@app.route("/auth")
def route_auth():
    token = oauth.internal_access.authorize_access_token()
    userinfo = oauth.internal_access.parse_id_token(token, nonce=session.get("nonce"))
    session["signed_in"] = True
    session["user"] = userinfo
    return redirect("/")

@app.route("/lists")
@RequireUser
def route_lists():
    lists = grist.fetch_table("GroupMetadata")
    print(lists)
    return render_template("groups.html", groups=lists)

if __name__ == "__main__":
    app.run(host="localhost", port=int(os.getenv("PORT", 5015)), debug=True)
