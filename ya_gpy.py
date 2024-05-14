import enum
import requests
import logging
from config import IAM_TOKEN, FOLDER_ID
logger = logging.getLogger(__name__)
logging.basicConfig(filename='logs.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    encoding='utf-8')
def get_token() -> str:
    url = "http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token"
    headers = {"Metadata-Flavor": "Google"}
    response = requests.request("GET", url, headers=headers)
    return response.json()["access_token"]
class YandexGptError(Exception):
    def __init__(self, *args, **kwargs):
        pass
    @staticmethod
    def __new__(*args, **kwargs):
        pass
class PyYandexGpt:
    def __init__(self,):
        self.token = IAM_TOKEN
        self.folder_id = FOLDER_ID
        self.gpt = 'yandexgpt'
        self.history = {}
    def create_request(self, user_id: int, prompt: str) -> requests.Response:
        url = f"https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        data = {
            "modelUri": f"gpt://{self.folder_id}/{self.gpt}/latest",
            "completionOptions": {
                "stream": False,
                "temperature": 0.5,
                "maxTokens": "80"
            },
            "messages": prompt
        }
        logging.info(f"запрос к API GPT: {data}")
        return requests.request("POST", url, json=data, headers=headers)
    def response(self, rep: requests.Response, user_id: int) -> dict:
        if rep.status_code != 200:
            raise YandexGptError("Response status code: " + str(rep.status_code))
        try:
            if "error" not in rep.json():
                result = rep.json()['result']['alternatives'][0]['message']['text']
                token = rep.json()['result']['usage']['totalTokens']
            else:
                if rep.json()['error']["message"] == "The token is invalid" or rep.json()['error']["message"] == "IAM token or API key has to be passed in request":
                    self.token = get_token()
                    self.create_request(user_id)
                    return {}
                else:
                    raise YandexGptError(rep.json()['error']["message"])
        except Exception as e:
            raise YandexGptError(e)
        return {"result": result, "tokens": token}
    def count_tokens(self, text: str) -> int:
        token = self.token
        folder_id = self.folder_id
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        data = {
            "modelUri": f"gpt://{folder_id}/yandexgpt/latest",
            "maxTokens": "500",
            "text": text
        }
        return len(
            requests.post(
                "https://llm.api.cloud.yandex.net/foundationModels/v1/tokenize",
                json=data,
                headers=headers
            ).json()['tokens']
        )