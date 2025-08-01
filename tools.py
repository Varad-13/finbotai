import requests
base_url = "https://dev.fridayy.ai"
def auth_vendor(phone_no):
    res = requests.post(base_url+"/ocr/auth/vendor/", json={"phone_no": phone_no})
    data = res.json()
    return {
        "user_token": data.get("access_token"),
        "store_id": data.get("store_id"),
        "new_user": data.get("new_user")
    }

def create_store(categories, token):
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.post(base_url+"/ocr/create_store/", json={"categories": categories}, headers=headers)
    return {"store_id": res.json().get("store_id")}

TOOL_MAPPING = {
    "auth_vendor": auth_vendor,
    "create_store": create_store
}
