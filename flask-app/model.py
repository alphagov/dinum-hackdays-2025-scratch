from grist_api import GristDocAPI
import os
from dotenv import load_dotenv

load_dotenv()  # take environment variables

GRIST_DOC_ID = os.getenv("GRIST_DOCUMENT_ID")
GRIST_SERVER = os.getenv("GRIST_SERVER")

grist = GristDocAPI(GRIST_DOC_ID, server=GRIST_SERVER)


def get_groups_for_user(email):
    all_groups = grist.fetch_table("GroupMetadata")
    user_groups = grist.fetch_table("Membership", filters={"UserEmail": email})
    groups_user_owns = filter(lambda ul: ul.MemberType == "Owner", user_groups)

    def is_member(group):
        return group.ID2 in map(lambda ul: ul.GroupID, user_groups)

    def is_admin(group):
        return group.ID2 in map(lambda ul: ul.GroupID, groups_user_owns)

    def convert_group(group):
        l = {
            "group_id": group.ID2,
            "group_name": group.GroupName,
            "is_member": is_member(group),
            "is_admin": is_admin(group),
        }
        return l

    return map(convert_group, all_groups)


def get_group_as_user(group_id, email):
    group = grist.fetch_table("GroupMetadata", filters={"ID2": group_id})
    if not group:
        return None

    user_groups = grist.fetch_table(
        "Membership", filters={"UserEmail": email, "GroupID": group_id}
    )

    def is_member():
        return len(user_groups) > 0

    def is_admin():
        return len(list(filter(lambda ul: ul.MemberType == "Owner", user_groups))) > 0

    return {
        "group_id": group[0].ID2,
        "group_name": group[0].GroupName,
        "is_member": is_member(),
        "is_admin": is_admin(),
    }


def join_group(user_email, group_id):
    # Check if the user is already a member of the group
    is_member = grist.fetch_table("Membership", filters={"UserEmail": user_email, "GroupID": group_id})
    if len(is_member) > 0:
        return True

    grist.add_records("Membership", [{
        "UserEmail": user_email,
        "GroupID": group_id,
        "MemberType": "Member"
    }])

    return True

def leave_group(user_email, group_id):
    # Check if the user is a member of the group
    is_member = grist.fetch_table("Membership", filters={"UserEmail": user_email, "GroupID": group_id})
    if len(is_member) == 0:
        return True

    grist.delete_records("Membership", [is_member[0].id])

    return True