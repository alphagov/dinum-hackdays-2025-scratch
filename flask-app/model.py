from grist_api import GristDocAPI
import os
from dotenv import load_dotenv
load_dotenv()  # take environment variables

GRIST_DOC_ID = os.getenv("GRIST_DOCUMENT_ID")
GRIST_SERVER = os.getenv("GRIST_SERVER")

grist = GristDocAPI(GRIST_DOC_ID, server=GRIST_SERVER)

def get_lists_for_user(email):
    all_lists = grist.fetch_table("GroupMetadata")
    user_lists = grist.fetch_table("Membership", filters={"UserEmail": email})

    def convert_list(list):
        print(list)
        l = {
            "group_id": list.get("GroupID"),
            "group_name": list.get("GroupName"),
            "is_member": list.get("GroupID") in map(lambda ul: ul.get("GroupID"), user_lists),
        }
        return l

    lists = map(convert_list, all_lists)

    return lists