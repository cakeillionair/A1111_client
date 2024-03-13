import base64
import json
import os
from time import sleep
from urllib.error import URLError
from urllib.request import urlopen

import requests

WORKING_DIR = os.getcwd()
A1111_FOLDER = ""

url = "http://127.0.0.1:7860"
server_url = "http://127.0.0.1:5000"


def get_a1111_folder():
    global A1111_FOLDER
    a1111 = input("A1111 folder?: ")
    while not (os.path.exists(a1111) and os.listdir(a1111).__contains__("webui.bat")):
        print("input invalid!")
        a1111 = input("A1111 folder?: ")
    A1111_FOLDER = a1111


def launch_a1111(folder):
    is_launched = False
    try:
        site = urlopen(url)
    except URLError as e:
        print("launching A1111")
    else:
        is_launched = True
    if not is_launched:
        os.chdir(folder)
        os.startfile("webui.bat")
        sleep(16)


def encode_image(path):
    with open(path, "rb") as file:
        return base64.b64encode(file.read()).decode()


if __name__ == '__main__':
    get_a1111_folder()
    launch_a1111(A1111_FOLDER)
    all_images_sent = False
    while not all_images_sent:
        response = requests.get(url=f'{server_url}/post_request')
        response_json = response.json()
        request_id = ""
        if response_json["status"] == "Request received":
            request_id = response_json["request_id"]
            while True:
                sleep(3)
                data = requests.get(url=f'{server_url}/get_image/' + str(request_id)).json()
                if data["status"] == "Finished":
                    init_images = [data["image"]]
                    payload = json.load(open(os.path.join(WORKING_DIR, "config_old.json")))
                    payload["init_images"] = init_images
                    a1111_response = requests.post(url=f'{url}/sdapi/v1/img2img', json=payload).json()
                    image = a1111_response['images'][0]
                    while True:
                        sleep(3)
                        r = requests.get(url=f'{server_url}/request_queue_status').json()
                        if r["status"] == "Queue is free":
                            image_payload = {
                                "image": image,
                                "image_id": data["image_id"]
                            }
                            requests.post(url=f'{server_url}/send_image', json=image_payload)
                            break
                    break
        elif response_json["status"] == "All images sent":
            all_images_sent = True
