from flask import session, redirect, url_for
from functools import wraps


def RequireUser(f):
    @wraps(f)
    def wrap(*args, **kwds):
        try:
            signed_in = session.get("signed_in", False)
            if signed_in:
                return f(*args, **kwds)
            else:
                session.clear()
        except Exception as e:
            print("auth_helpers: RequireUser:", e)
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
