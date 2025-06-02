import os

from flask import session, redirect, url_for, request
from functools import wraps

DOMAINS_ALLOWED_CREATE_GROUP = [
    domain.strip().lower()
    for domain in os.getenv(
        "DOMAINS_ALLOWED_CREATE_GROUP",
        "gov.uk,nhs.net",
    ).split(",")
    if domain.strip()
]


def can_create_group(email=None):
    can = False
    if email:
        domain = email.split("@")[-1].lower()
        for allowed_domain in DOMAINS_ALLOWED_CREATE_GROUP:
            if domain == allowed_domain or domain.endswith("." + allowed_domain):
                can = True
                break
    return can


def RequireUser(f):
    @wraps(f)
    def wrap(*args, **kwds):
        signed_in = False
        user = {}
        try:
            signed_in = session.get("signed_in", False)
            user = session.get("user", {})
        except Exception as e:
            print("auth_helpers: RequireUser:", e)

        if signed_in and user:
            return f(*args, **kwds)
        else:
            session.clear()

        session["redirect_url"] = request.url
        return redirect(url_for("route_login"))

    return wrap


def UserOptional(f):
    @wraps(f)
    def wrap(*args, **kwds):
        try:
            signed_in = session.get("signed_in", False)
            if not signed_in:
                session.clear()
        except Exception as e:
            print("auth_helpers: UserOptional:", e)
        return f(*args, **kwds)

    return wrap
