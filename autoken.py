import requests
def get_token() -> str:
    url = "http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token"
    headers = {"Metadata-Flavor": "Google"}
    response = requests.request("GET", url, headers=headers)
    return response.json()["access_token"]
def update_config_file():
    with open('config.py', 'r') as file:
        content = file.read()
    new_token = get_token()
    content = content.replace('IAM_TOKEN = "old_token_value"', f'IAM_TOKEN = "{new_token}"')
    with open('config.py', 'w') as file:
        file.write(content)