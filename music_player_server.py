#!/usr/bin/env python

# WS server example that synchronizes state across clients

# https://websockets.readthedocs.io/en/stable/intro/index.html
# https://pypi.org/project/audioplayer/
import asyncio
import json
import logging
import websockets
import os
from audioplayer import AudioPlayer

USERNAME = "admin"
PASSWORD = "admin"
BASE_FOLDER = "C:\\"

logging.basicConfig()

STATE = {"value": 0}

USERS = set()
USERS_AUTH = set()
VOLUME = 100
GLOBAL_FILE_DIR = ""
GLOBAL_PLAYER = AudioPlayer("")

def global_file_dir(file_dir):
    global GLOBAL_FILE_DIR
    GLOBAL_FILE_DIR = file_dir

def global_player_start_song():
    global GLOBAL_PLAYER
    GLOBAL_PLAYER = AudioPlayer(GLOBAL_FILE_DIR)
    GLOBAL_PLAYER.play()

def global_player_play():
    GLOBAL_PLAYER.resume()

def global_player_stop():
    GLOBAL_PLAYER.stop()

def global_player_pause():
    GLOBAL_PLAYER.pause()

def global_volume_minus():
    global VOLUME
    if VOLUME > 0:
        VOLUME = VOLUME - 1
        return True
    else:
        return False

def global_volume_plus():
    global VOLUME
    if VOLUME < 100:
        VOLUME = VOLUME + 1
        return True
    else:
        return False

def state_event():
    return json.dumps({"type": "state", **STATE})

def error_event(description):
    return json.dumps({"type": "error", "description": description})

def success_event(description):
    return json.dumps({"type": "success", "description": description})

def login_event(status):
    return json.dumps({"type": "login_status", "login_success": status})

def users_event():
    return json.dumps({"type": "users", "count": len(USERS)})

def volume_var(volume):
    return json.dumps({"type": "volume_var", "values": volume})

def list_dir(dir, data):
    return json.dumps({"type": "folder_list", "dir": dir, "data": data})

def users_welcome():
    return json.dumps({"type": "welcome", "msg": "Hello from Kien Music Server"})

async def counter(websocket, path):
    try:
        # Register user
        USERS.add(websocket)
        # websockets.broadcast(USERS, users_event())
        print(USERS)
        print(users_event())
        # Send current state to user
        await websocket.send(users_welcome())
        # Manage state changes
        async for message in websocket:
            try:
                data = json.loads(message)
            except:
                data = {}
                data["action"] = "None"
                await websocket.send(error_event("Json has been sabotaged"))
            if data["action"] == "auth":
                if websocket not in USERS_AUTH:
                    try:
                        if(data["username"] == USERNAME and data["password"] == PASSWORD):
                            USERS_AUTH.add(websocket)
                            await websocket.send(login_event("TRUE"))
                        else:
                            await websocket.send(login_event("FALSE"))
                    except:
                        await websocket.send(error_event("Can not find username and password in package"))
                else:
                    await websocket.send(error_event("User has logged in"))
            elif data["action"] == "folder_list":
                if websocket in USERS_AUTH:
                    try:
                        recv_folder = data["dir"]
                        data_dir = []
                        for item in os.listdir(recv_folder):
                            iteml = os.path.join(recv_folder, item)
                            if os.path.isfile(iteml):
                                # print(item + " is a file")
                                item_data = {"name": item, "type": 1}
                                data_dir.append(item_data)
                            elif os.path.isdir(iteml):
                                # print(item + " is a dir")
                                item_data = {"name": item, "type": 0}
                                data_dir.append(item_data)
                            else:
                                print("Unknown!")
                        data_dir = sorted(data_dir, key=lambda k: k['type'])
                        await websocket.send(list_dir(recv_folder, data_dir))
                        print(data_dir)
                    except:
                        await websocket.send(error_event("Not received right folder"))
                        print("Not received right folder")
                else:
                    print("Not authorized")
                    await websocket.send(error_event("Not authorized"))

            elif data["action"] == "vol_minus":
                if global_volume_minus():
                    print("Volume has been decreased")
                    websockets.broadcast(USERS, volume_var(VOLUME))
                else:
                    await websocket.send(error_event("Volume already lowest it can be"))
            elif data["action"] == "vol_plus":
                if global_volume_plus():
                    print("Volume has been increased")
                    websockets.broadcast(USERS, volume_var(VOLUME))
                else:
                    await websocket.send(error_event("Volume already highest it can be"))

            elif data["action"] == "start_music_song":
                print("Music start")
                # force authenticate within
                if websocket in USERS_AUTH:
                    try:
                        dir = data["directory"]
                    except:
                        dir = ""

                    # start music
                    global_file_dir(dir)
                    global_player_start_song()

                    await websocket.send(success_event("Music started"))
                else:
                    print("Not authorized")
                    await websocket.send(error_event("Not authorized"))
            elif data["action"] == "play_music":
                if websocket in USERS_AUTH:
                    global_player_play()

                    await websocket.send(success_event("Music continued"))
                else:
                    print("Not authorized")
                    await websocket.send(error_event("Not authorized"))
            elif data["action"] == "stop_music":
                print("Music stop")

                global_player_stop()
                await websocket.send(success_event("Music stopped"))
            elif data["action"] == "pause_music":
                print("Music paused")

                global_player_pause()
                await websocket.send(success_event("Music paused"))
            elif data["action"] == "None":
                print("Do not thing")
            else:
                logging.error("Unsupported event: %s", data)
    finally:
        # Unregister user
        USERS.remove(websocket)
        # websockets.broadcast(USERS, users_event())
        # Disconnect authorized user to avoid collapse
        USERS_AUTH.remove(websocket)


async def main():
    async with websockets.serve(counter, "localhost", 6789):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())