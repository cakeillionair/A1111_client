import base64
import datetime
import json
import os
import socket
from time import sleep
from urllib.error import URLError
from urllib.request import urlopen

import requests

WORKING_DIR = os.getcwd()
A1111_FOLDER = ""
LOG_FOLDER_PATH = os.path.join(WORKING_DIR, "logs")

LOG_FLAG = True

client = socket.gethostname()
client_ip = socket.gethostbyname(client)

url = "http://127.0.0.1:7860"
server_url = "http://127.0.0.1:5000"


# Falls der Ordner in der Configdatei nicht gesetzt ist, wird er angefragt
def get_a1111_folder():
    global A1111_FOLDER
    a1111 = input("A1111 folder?: ")
    while not (os.path.exists(a1111) and os.listdir(a1111).__contains__("webui.bat")):
        print("input invalid!")
        a1111 = input("A1111 folder?: ")
    A1111_FOLDER = a1111


# Diese Methode startet A1111, falls es nicht schon gestartet ist
def launch_a1111(folder):
    is_launched = False
    # Es wird versucht sich mit A1111 zu verbinden
    try:
        site = urlopen(url)
    except URLError as e:
        write_out_log("Starting A1111!", LOG)
    else:
        # Wenn es klappt, ist A1111 schon gestartet
        is_launched = True
    if not is_launched:
        # A1111 wird gestartet und das Programm wartet bis es fertig ist
        os.chdir(folder)
        os.startfile("webui.bat")
        sleep(client_config["start_time"])
    else:
        write_out_log("A1111 already launched!", LOG)


# Diese Methode enkodiert Bilder um sie zu verschicken
def encode_image(path):
    with open(path, "rb") as file:
        return base64.b64encode(file.read()).decode()


# Diese Methode beschreibt eine Logdatei und gibt die Nachricht auch in der Konsole aus
def write_out_log(msg, log):
    # Es wird nur in die Logdatei geschrieben, wenn nichts schiefging
    if LOG_FLAG:
        log.write("[" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "]: " + msg + "\n")
    print(msg)


# Diese Methode fügt erhaltende Bilder der Bilderdatei hinzu
def add_image_to_list(msg, image_list):
    image_list.write(msg + "\n")


# Hier wird die Logdatei erzeugt, wo Informationen während des Laufens des Programms geschrieben werden und es wird eine
# Datei mit allen Bildern, die vom Client bearbeitet werden, gemacht
def create_log():
    global LOG_FLAG
    new = False
    # Gibt es den Standartordner nicht, wird er erzeugt
    if not os.path.exists(LOG_FOLDER_PATH):
        os.mkdir(LOG_FOLDER_PATH)
        new = True
    # Datum und Uhrzeit kommen in den Namen der Logdatei
    date = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log = open(os.path.join(LOG_FOLDER_PATH, date + "_A1111_image_processing_client_log.txt"), "a")
    # Bilderdatei wird genauso erzeugt
    image_list = open(os.path.join(LOG_FOLDER_PATH, date + "_client_image_list.txt"), "a")
    if (not log) or (
            not os.path.exists(os.path.join(LOG_FOLDER_PATH, date + "_A1111_image_processing_client_log.txt"))):
        # Falls etwas beim Erzeugen der Logdatei schiefgeht, wird nichts mehr in sie geschrieben
        LOG_FLAG = False
        print("Error: Something went wrong during log creation!")
    else:
        if new:
            # Ist der Ordner neu, wird das angegeben
            write_out_log("Log folder created!", log)
        write_out_log("Log file created!", log)
    return log, image_list


# Main Methode die beim Starten des Programms ausgeführt wird
if __name__ == '__main__':
    # Erstellt eine Logdatei
    LOG, IMAGE_LIST = create_log()
    write_out_log("Client started with IP: " + client_ip + "!", LOG)
    # Lädt die Configdatei des Clients mit den Einstellungen
    client_config = json.load(open(os.path.join(WORKING_DIR, "client_config.json")))
    # Wenn die Configdatei nicht aktiviert ist, müssen die Ordner in der Konsole angefragt werden
    if not client_config["use_client_config"]:
        get_a1111_folder()
    else:
        A1111_FOLDER = client_config["folders"]["A1111_folder"]
    write_out_log("A1111 folder set to: " + A1111_FOLDER, LOG)
    # A1111 wird gestartet, falls es nicht schon läuft
    launch_a1111(A1111_FOLDER)
    all_images_sent = False
    timeout = client_config["timeout"]
    s = requests.Session()
    # Während der Client die Nachricht, dass alle Bilder verschickt wurden, nicht erhält, bearbeitet er Bilder
    while not all_images_sent:
        write_out_log("Requesting image from server!", LOG)
        # Sendet Anfrage zum Server
        response = s.get(url=f'{server_url}/post_request', timeout=timeout).json()
        request_id = ""
        if response["status"] == "Finished":
            # Anfrage war erfolgreich
            request_id = response["request_id"]
            image_id = str(response["image_id"])
            write_out_log("Received image: " + response["file_name"] + ", ID: "
                          + request_id + ", Image ID: " + image_id + "!", LOG)
            # Bild wird zur Bilderdatei hinzugefügt
            add_image_to_list(response["file_name"] + ", ID: "
                              + request_id + ", Image ID: " + image_id + "!", IMAGE_LIST)
            init_images = [response["image"]]
            # API-payload wird erzeugt
            payload = json.load(open(os.path.join(WORKING_DIR, "config.json")))
            payload["init_images"] = init_images
            write_out_log("Sending image to A1111! ID: " + request_id + ", Image ID: " + image_id + "!", LOG)
            # Bild wird alle 30 Sekunden zu A1111 geschickt, bis A1111 was zurückschickt
            a1111_response = s.post(url=f'{url}/sdapi/v1/img2img', json=payload, timeout=timeout).json()
            while "images" not in a1111_response:
                write_out_log("A1111 is busy, trying again in 30 seconds!", LOG)
                sleep(30)
                a1111_response = s.post(url=f'{url}/sdapi/v1/img2img', json=payload, timeout=timeout).json()
            image = a1111_response['images'][0]
            write_out_log("Received image from A1111! ID: " + request_id + ", Image ID: " + image_id + "!", LOG)
            # Server-payload wird erzeugt
            image_payload = {
                "image": image,
                "image_id": response["image_id"],
                "file_name": response["file_name"]
            }
            write_out_log("Sending image to server! ID: " + request_id + ", Image ID: " + image_id + "!", LOG)
            # Verändertes Bild wird zum Server zurückgeschickt
            s.post(url=f'{server_url}/send_image', json=image_payload, timeout=timeout)
            write_out_log("Sent image! ID: " + request_id + ", Image ID: " + image_id + "!", LOG)
        elif response["status"] == "All images sent":
            # Client schaltet ab, da alle Bilder verschickt wurden
            write_out_log("All images sent! Shutting down!", LOG)
            all_images_sent = True
        elif response["status"] == "Cannot handle requests right now":
            # Client muss warten, da der Server noch auf andere Clients wartet
            write_out_log("Other clients currently handling images. Waiting 30 seconds to try again!", LOG)
            sleep(30)
        else:
            # Es gab einen unbekannten Fehler, was den Client abschaltet
            write_out_log("Error: Received invalid response from server! Shutting down!", LOG)
            all_images_sent = True
