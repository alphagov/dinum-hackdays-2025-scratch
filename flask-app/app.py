#!/usr/bin/env python3

import os
from flask import Flask, redirect, url_for, session, render_template, request, flash
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from auth_helpers import RequireUser, UserOptional, can_create_group
from design_helpers import design_dictionary
from model import (
    get_groups_for_user,
    get_group_as_user,
    join_group,
    leave_group,
    create_group,
    delete_group,
    save_group,
)
from flask_wtf.csrf import CSRFProtect
import qrcode
import io
import base64

load_dotenv()  # take environment variables

DESIGN_TYPE = os.getenv("DESIGN_TYPE", "govuk").lower()

app = Flask(__name__, template_folder="templates", static_folder="assets")
app.secret_key = os.getenv("SECRET_KEY", os.urandom(24))

app.jinja_env.globals.update(
    design_type=DESIGN_TYPE,
    design_dictionary=design_dictionary[DESIGN_TYPE],
)
csrf = CSRFProtect(app)

OPENID_CONFIG_URL = os.getenv(
    "OPENID_CONFIG_URL",
    "https://sso.service.security.gov.uk/.well-known/openid-configuration",
)
CLIENT_ID = os.getenv("CLIENT_ID")

oauth = OAuth(app)
oauth.register(
    name="internal_access",
    server_metadata_url=OPENID_CONFIG_URL,
    client_id=CLIENT_ID,
    client_secret=os.getenv("CLIENT_SECRET"),
    client_kwargs={"scope": "openid profile email"},
)


@app.route("/")
@UserOptional
def route_root():
    user = session.get("user", {})
    return render_template(
        "root.html",
        user=user,
        navigation=[
            {"label": "Home", "url": url_for("route_root"), "active": True},
            {"label": "Groups", "url": url_for("route_groups")},
            {
                "label": "Logout" if user else "Login",
                "url": url_for("route_logout") if user else url_for("route_login"),
            },
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
    userinfo = oauth.internal_access.parse_id_token(token, nonce=session.pop("nonce"))
    if userinfo:
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


@app.route("/save-group", methods=["POST"])
@RequireUser
def route_save_group():
    group_id = request.form.get("group_id", "").strip()
    if not group_id:
        return "Unknown group", 404

    group_desc = request.form.get("group_desc", "").strip()
    group_visibility = request.form.get("group_visibility", "Private").strip().title()
    if group_visibility not in ["Private", "Authorised", "Any"]:
        return "Invalid group visibility", 400

    group_changes = {
        "GroupID": group_id,
        "GroupDesc": group_desc,
        "GroupVisibility": group_visibility,
        "AllowSelfJoin": request.form.get("AllowJoin", "").strip() == "AllowJoin",
        "AllowSelfLeave": request.form.get("AllowLeave", "").strip() == "AllowLeave",
    }

    success = save_group(group_changes)
    if success:
        flash("Group updated successfully", "success")
        return redirect(f"/group/{group_id}#settings")

    return "Error", 500


@app.route("/delete-group", methods=["POST"])
@RequireUser
def route_delete_group():
    user = session.get("user", {})
    email = user.get("email")

    group_id = request.form.get("group_id", "").strip()
    if not group_id:
        return "Unknown group", 404

    success = delete_group(group_id, email)
    if success:
        flash("Group deleted successfully", "success")
        return redirect(url_for("route_groups"))

    return "Failed to delete group", 400


@app.route("/new-group", methods=["GET", "POST"])
@RequireUser
def route_new_group():
    user = session.get("user", {})
    email = user.get("email")

    if not can_create_group(email):
        return redirect("/")

    is_post = request.method == "POST"
    group = {}

    if is_post:
        group = {
            "group_name": request.form.get("group_name", "").strip(),
            "group_desc": request.form.get("group_desc", "").strip(),
            "group_visibility": request.form.get("group_visibility", "Private"),
        }
        group_name = group["group_name"]
        if group_name:
            flash(f'Group "{group_name}" created successfully', "success")
            group_id = create_group(group=group, user_email=email)
            if group_id:
                return redirect(f"/group/{group_id}#settings")

    return render_template(
        "group_new.html",
        is_post=is_post,
        group=group,
        navigation=[
            {"label": "Home", "url": url_for("route_root")},
            {"label": "Groups", "url": url_for("route_groups"), "active": True},
            {"label": "Logout", "url": url_for("route_logout")},
        ],
    )


@app.route("/group/<group_id>/leave")
@app.route("/group/<group_id>/join")
@UserOptional
def route_group_members_join(group_id: str = None):
    user = session.get("user", {})
    email = user.get("email", None)

    if not email and request.args.get("login") == "true":
        session["redirect_url"] = request.url
        return redirect(url_for("route_login"))

    group = get_group_as_user(group_id, email, with_members=False)
    if not group:
        return redirect(url_for("route_not_found"))

    url = url_for("route_group_members_join", group_id=group_id, _external=True)

    qr = qrcode.QRCode(
        version=1,  # controls the size of the QR code (1 = 21×21). Increase for more data.
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,  # pixel size of each “box” in the QR
        border=4,  # thickness of the border (minimum is 4 according to specs)
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # 3. Write the image to an in-memory buffer as PNG:
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    png_bytes = buffer.getvalue()
    buffer.close()

    # 4. Encode those PNG bytes as Base64, then build a data URI:
    b64 = base64.b64encode(png_bytes).decode("ascii")
    data_uri = f"data:image/png;base64,{b64}"

    return render_template(
        "group_member_join.html",
        group=group,
        user=user,
        navigation=[
            {"label": "Home", "url": url_for("route_root")},
            {"label": "Groups", "url": url_for("route_groups"), "active": True},
            {
                "label": "Logout" if user else "Login",
                "url": url_for("route_logout") if user else "?login=true",
            },
        ],
        qr_code_data_uri=data_uri,
        url=url,
    )


@app.route("/group/<group_id>/members.csv")
@RequireUser
def route_group_members_csv(group_id: str = None):

    user = session.get("user", {})
    email = user.get("email")

    group = get_group_as_user(group_id, email)
    if not group:
        return redirect(url_for("route_not_found"))

    csv = "email_address,member_type\n"
    for member in group.get("members", []):
        csv += f"{member.UserEmail},{member.MemberType}\n"

    response = app.response_class(
        response=csv,
        status=200,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{group["group_name"]}.csv"'
        },
    )
    return response


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
        can_create_group=can_create_group(email),
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
    from_page = request.form.get("from_page")

    success = join_group(email, group_id)

    if success:
        flash("Successfully joined group", "success")
        if from_page == "group_member_join":
            return redirect(url_for("route_group_members_join", group_id=group_id))
        return redirect(url_for("route_groups"))
    else:
        return "Failed to join group", 400


@app.route("/leave/<group_id>", methods=["POST"])
@RequireUser
def route_leave_group(group_id):
    user = session.get("user", {})
    email = user.get("email")
    from_page = request.form.get("from_page")

    success = leave_group(email, group_id)

    if success:
        flash("Successfully left group", "success")
        if from_page == "group_member_join":
            return redirect(url_for("route_group_members_join", group_id=group_id))
        return redirect(url_for("route_groups"))
    else:
        return "Failed to leave group", 400


if __name__ == "__main__":
    app.run(host="localhost", port=int(os.getenv("PORT", 5015)), debug=True)
