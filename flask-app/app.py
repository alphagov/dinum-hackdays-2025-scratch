#!/usr/bin/env python3

import os
from flask import Flask, redirect, url_for, session, render_template
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from auth_helpers import RequireUser, UserOptional
<<<<<<< HEAD
from model import get_groups_for_user, get_group_as_user
=======
from model import get_groups_for_user, join_group, leave_group
>>>>>>> af8db0e (add join/leave group buttons)

load_dotenv()  # take environment variables

app = Flask(__name__, template_folder="templates", static_folder="assets")
app.secret_key = os.getenv("SECRET_KEY", os.urandom(24))

CLIENT_ID = os.getenv("CLIENT_ID")

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
            {"label": "Groups", "url": url_for("route_groups")},
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
    return redirect(session.pop("redirect_url", "/"))


@app.route("/group/<group_id>")
@RequireUser
def route_group_indiv(group_id: str = None):

    user = session.get("user", {})
    email = user.get("email")

    group = get_group_as_user(group_id, email)
    if not group:
        return redirect(url_for("route_not_found"))

    return render_template(
        "group_indiv.html",
        group=group,
        navigation=[
            {"label": "Home", "url": url_for("route_root")},
            {"label": "Groups", "url": url_for("route_groups"), "active": True},
            {"label": "Logout", "url": url_for("route_logout")},
        ],
    )


@app.route("/group/<group_id>/members")
@RequireUser
def route_group_members(group_id: str = None):

    user = session.get("user", {})
    email = user.get("email")

    group = get_group_as_user(group_id, email)
    if not group:
        return redirect(url_for("route_not_found"))

    return render_template(
        "group_members.html",
        group=group,
        navigation=[
            {"label": "Home", "url": url_for("route_root")},
            {"label": "Groups", "url": url_for("route_groups"), "active": True},
            {"label": "Logout", "url": url_for("route_logout")},
        ],
    )


@app.route("/not-found")
@UserOptional
def route_not_found():
    user = session.get("user", {})
    return render_template(
        "not_found.html",
        navigation=[
            {"label": "Home", "url": url_for("route_root")},
            {"label": "Groups", "url": url_for("route_groups"), "active": True},
            {
                "label": "Logout" if user else "Login",
                "url": url_for("route_logout") if user else url_for("route_login"),
            },
        ],
    )


@app.route("/groups")
@RequireUser
def route_groups():
    user = session.get("user", {})
    email = user.get("email")
    groups = get_groups_for_user(email)
    return render_template(
        "groups.html",
        groups=groups,
        navigation=[
            {"label": "Home", "url": url_for("route_root")},
            {"label": "Groups", "url": url_for("route_groups"), "active": True},
            {"label": "Logout", "url": url_for("route_logout")},
        ],
    )

@app.route("/join/<group_id>", methods=["POST"])
@RequireUser
def route_join_group(group_id):
    user = session.get("user", {})
    email = user.get("email")
    
    success = join_group(email, group_id)
    
    if success:
        return redirect(url_for("route_groups"))
    else:
        return "Failed to join group", 400
    
@app.route("/leave/<group_id>", methods=["POST"])
@RequireUser
def route_leave_group(group_id):
    user = session.get("user", {})
    email = user.get("email")
    
    success = leave_group(email, group_id)
    
    if success:
        return redirect(url_for("route_groups"))
    else:
        return "Failed to leave group", 400

if __name__ == "__main__":
    app.run(host="localhost", port=int(os.getenv("PORT", 5015)), debug=True)
