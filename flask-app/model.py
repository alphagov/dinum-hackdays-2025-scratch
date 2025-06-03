from grist_api import GristDocAPI
import os
import uuid
from dotenv import load_dotenv
import functools
from flask import request

load_dotenv()  # take environment variables

GRIST_DOC_ID = os.getenv("GRIST_DOCUMENT_ID")
GRIST_SERVER = os.getenv("GRIST_SERVER")

grist = GristDocAPI(GRIST_DOC_ID, server=GRIST_SERVER)


def save_group(group_changes):
    try:
        group_id = group_changes.get("GroupID", "")
        group = grist.fetch_table("GroupMetadata", filters={"ID2": group_id})
        if not group:
            return None

        group_changes["id"] = group[0].id
        group_changes["ID2"] = group_changes.pop("GroupID")

        grist.update_records(
            "GroupMetadata",
            [group_changes],
        )
    except Exception as e:
        print(f"Error saving group: {e}")
        return False

    return True


def create_group(group, user_email):
    # create a new group in the GroupMetadata table
    group_id = str(uuid.uuid4())

    group_visibility = group.get("group_visibility", "Private").title()
    if group_visibility not in ["Private", "Authorised", "Any"]:
        return None

    grist.add_records(
        "GroupMetadata",
        [
            {
                "GroupName": group["group_name"],
                "GroupDesc": group.get("group_desc", ""),
                "GroupVisibility": group_visibility,
                "AllowSelfJoin": True,
                "AllowSelfLeave": True,
                "ID2": group_id,
            }
        ],
    )
    # add the user as an owner of the group in the Membership table
    grist.add_records(
        "Membership",
        [
            {
                "UserEmail": user_email,
                "GroupID": group_id,
                "MemberType": "Owner",
            }
        ],
    )

    return group_id


def delete_group(group_id, user_email):
    group = get_group_as_user(group_id, user_email)
    if not group or not group["is_admin"]:
        return False

    # delete the group from the GroupMetadata table
    grist.delete_records("GroupMetadata", [group.get("_id")])

    members = grist.fetch_table("Membership", filters={"GroupID": group_id})
    # delete all members from the Membership table
    if members:
        grist.delete_records("Membership", [m.id for m in members])

    return True


def get_groups_for_user(email):
    all_groups = grist.fetch_table("GroupMetadata")
    user_groups = grist.fetch_table("Membership", filters={"UserEmail": email})
    groups = [
        get_group_as_user(
            grp.ID2, email=email, user_groups=user_groups, with_members=False
        )
        for grp in all_groups
    ]
    return [
        grp for grp in groups if grp and grp["visibility_for_user"] or grp["is_member"]
    ]


def split_string_to_list(string):
    if not string:
        return []
    return [s.strip().lower() for s in string.split(",") if s.strip()]


@functools.cache
def _fetch_all_groups(vary):
    print(f"Fetching all groups with vary={vary}")
    return grist.fetch_table("GroupMetadata")


def fetch_all_groups():
    return _fetch_all_groups(request.environ.get("REQUEST_ID", ""))


@functools.cache
def _fetch_all_members(vary):
    print(f"Fetching all members with vary={vary}")
    return grist.fetch_table("Membership")


def fetch_all_members():
    return _fetch_all_members(request.environ.get("REQUEST_ID", ""))


def get_group_as_user(group_id, email: str = None, user_groups={}, with_members=True):
    group = list(filter(lambda g: g.ID2 == group_id, fetch_all_groups()))
    if not group:
        return None

    if email:
        email = email.lower().strip()

    user_groups = {}
    if email and not user_groups:
        user_groups = list(
            filter(
                lambda g: g.UserEmail.lower().strip() == email
                and g.GroupID == group_id,
                fetch_all_members(),
            )
        )

    def is_member():
        return any(
            ul.GroupID == group_id
            for ul in user_groups
            if ul.GroupID == group_id and ul.UserEmail.lower().strip() == email
        )

    def is_admin():
        return any(
            ul.GroupID == group_id
            for ul in user_groups
            if ul.GroupID == group_id
            and ul.UserEmail.lower().strip() == email
            and ul.MemberType == "Owner"
        )

    members = []
    if with_members:
        members = [m for m in fetch_all_members() if m.GroupID == group_id]
        # sort members by email
        members.sort(key=lambda m: m.UserEmail.lower().strip())

    allowed_domains = split_string_to_list(group[0].AllowedDomains) or []
    allowed_emails = split_string_to_list(group[0].AllowedEmails) or []

    visibility_for_user = False
    if group[0].GroupVisibility in ["Authorised", "Private"]:
        if email:
            if email in allowed_emails:
                visibility_for_user = True
            elif any(
                email.endswith(domain.replace("*.", ".")) for domain in allowed_domains
            ):
                visibility_for_user = True
            elif any(
                email.endswith(f"@{domain}")
                for domain in allowed_domains
                if "*" not in domain
            ):
                visibility_for_user = True
    elif group[0].GroupVisibility == "Any":
        visibility_for_user = True

    could_join = email and visibility_for_user and group[0].AllowSelfJoin
    could_leave = email and visibility_for_user and group[0].AllowSelfLeave

    return {
        "_id": group[0].id,
        "group_id": group[0].ID2,
        "group_name": group[0].GroupName,
        "members": members,
        "is_member": is_member(),
        "is_admin": is_admin(),
        "description": group[0].GroupDesc,
        "group_visibility": group[0].GroupVisibility,
        "visibility_for_user": visibility_for_user,
        "allowed_domains": allowed_domains,
        "allowed_emails": allowed_emails,
        "could_join": could_join,
        "could_leave": could_leave,
        "allow_self_join": group[0].AllowSelfJoin or False,
        "allow_self_leave": group[0].AllowSelfLeave or False,
    }


def join_group(user_email, group_id):
    # Check if the user is already a member of the group
    is_member = grist.fetch_table(
        "Membership", filters={"UserEmail": user_email, "GroupID": group_id}
    )
    if len(is_member) > 0:
        return True

    grist.add_records(
        "Membership",
        [{"UserEmail": user_email, "GroupID": group_id, "MemberType": "Member"}],
    )

    return True


def leave_group(user_email, group_id):
    # Check if the user is a member of the group
    is_member = grist.fetch_table(
        "Membership", filters={"UserEmail": user_email, "GroupID": group_id}
    )
    if len(is_member) == 0:
        return True

    grist.delete_records("Membership", [is_member[0].id])

    return True
