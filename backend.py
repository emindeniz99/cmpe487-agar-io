import os
from threading import Thread
import time
import sys
import json
import socket
from enum import IntEnum
import select
import subprocess
import math
import random
import shared


def get_ip():
    # https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib/28950776#28950776
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('8.8.8.8', 80))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


myIP = get_ip()  # or "192.168.1.101"

print("Hello, IP: "+myIP)
print("Welcome to agar.io")


class messageTypes(IntEnum):
    DISCOVER = 1
    DISCOVER_RESPONSE = 2
    JOIN_GAME = 3
    NEW_GAME_RESPONSE = 4
    MOVE = 5
    CURRENT_STATE = 6


players = {
    'rand164': {'X': 643, 'Y': 276, 'score': 100, 'color': (72, 131, 158), 'name': 'testuser', 'IP': '192.168.1.153', 'timestamp': 1942681807848047000}

    # playerid:{
    #   X
    #   Y
    #   score
    #   color
    #   name
    # }
}

foods = [
    #  {
    #   x:
    #   y:
    #   color:
    #   size:
    # }
]

ipToIDmap = {

}


DISCO_PORT = 12345
MOVE_PORT = 12346
print("port=", DISCO_PORT)

RECVSIZE = 204800

gameStartTime = time.time_ns()

FOOD_DEFAULT_SIZE = 3


def UDPsendStatus():
    global players, foods, gameStartTime, ipToIDmap
    # message sender, CHAT
    while True:
        # print("UDPsendStatus")
        removeOfflineUsers()
        for playerID in players:
            player = players[playerID]
            if player["name"] == "testuser":
                continue
            STATE_MESSAGE_BYTES = json.dumps(
                {"type": messageTypes.CURRENT_STATE,
                 "players": players,
                 "foods": foods,
                 "timestamp": time.time_ns(),
                 "gametime": (time.time_ns()-gameStartTime)//10**3
                 })
            STATE_MESSAGE_BYTES = str.encode(STATE_MESSAGE_BYTES)
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.bind(("", 0))
                    for i in range(3):
                        sock.sendto(STATE_MESSAGE_BYTES,
                                    (player["IP"], MOVE_PORT))
            except:
                print("error")
        time.sleep(0.01)


def checkCollision(playerid):
    global foods, players
    print("hellooooooooo")
    player = players[playerid]
    for i, food in enumerate(foods[:]):
        dis = math.sqrt((player["X"] - food["X"]) **
                        2 + (player["Y"]-food["Y"])**2)
        if (math.sqrt(player["score"])) > dis:
            foods.remove(food)
            players[playerid]["score"] += food["size"]
    for id in dict(players):
        targetplayer = players[id]
        if playerid == id:
            continue
        if targetplayer["score"] < player["score"]:
            dis = math.sqrt((player["X"] - targetplayer["X"]) **
                            2 + (player["Y"]-targetplayer["Y"])**2)
            if (math.sqrt(player["score"])) > dis:
                players[playerid]["score"] += math.sqrt(targetplayer["score"])

                players[id]["X"] = random.randint(30, shared.MAP_WIDTH-30)
                players[id]["Y"] = random.randint(30, shared.MAP_HEIGHT-30)
                players[id]["score"] = shared.INITIAL_SCORE
        else:
            dis = math.sqrt((player["X"] - targetplayer["X"]) **
                            2 + (player["Y"]-targetplayer["Y"])**2)
            if (math.sqrt(targetplayer["score"])) > dis:
                players[id]["score"] += math.sqrt(targetplayer["score"])

                players[playerid]["X"] = random.randint(
                    30, shared.MAP_WIDTH-30)
                players[playerid]["Y"] = random.randint(
                    30, shared.MAP_HEIGHT-30)
                players[playerid]["score"] = shared.INITIAL_SCORE
                players[playerid]["timestamp"] += 10**8  # TODO:
                players[playerid]["number_of_deaths"] += 1


def removeOfflineUsers():
    global players, ipToIDmap
    print(players, ipToIDmap)

    for ip in dict(ipToIDmap):
        if players[ipToIDmap[ip]]["timestamp"] == 0:
            continue
        if players[ipToIDmap[ip]]["timestamp"]+(5*10**9) < time.time_ns():
            print("OFFLINE USER", players[ipToIDmap[ip]]["name"])

            del players[ipToIDmap[ip]]
            del ipToIDmap[ip]


def messagegetterUDP():

    global players, foods, gameStartTime, ipToIDmap

    # listener, get messages and print, also DISCOVER_RESPONSE
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("", DISCO_PORT))
        s.setblocking(0)
        while True:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            result = select.select([s], [], [])
            msg, address = result[0][0].recvfrom(RECVSIZE)
            # print("addd", address[0])
            sender = address[0]
            # print("SENDER:: ", sender)
            message = json.loads(msg.decode('utf-8'))
            mesType = message["type"]
            if mesType == messageTypes.DISCOVER:
                # return discovery response
                print(message)
                # if str(sender) == myIP:
                #     continue
                print("..")
                if ipToIDmap.get(message["name"]) != None:
                    newPlayerID = ipToIDmap.get(message["name"])
                else:
                    newPlayerID = "random123"+str(random.randint(1, 200))
                newPlayer = {
                    "X": random.randint(30, shared.MAP_WIDTH-30),
                    "Y": random.randint(30, shared.MAP_HEIGHT-30),
                    "score": shared.INITIAL_SCORE,
                    "color": (random.randint(1, 255), random.randint(1, 255), random.randint(1, 255)),
                    "name": message["name"],
                    "IP": sender,
                    "timestamp": 0,
                    "number_of_deaths": 0
                }
                players[newPlayerID] = newPlayer

                sssss = (json.dumps(
                    {"type": messageTypes.DISCOVER_RESPONSE,
                     "playerid": newPlayerID,
                     "players": players,
                     "foods": foods
                     }))
                print(sssss)
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                        sock.connect((sender, DISCO_PORT))
                        sock.sendall(sssss.encode('utf-8'))
                    ipToIDmap[message["name"]] = newPlayerID
                    # print("sent, response")
                except Exception as e:
                    print("response  error: ", e)

            elif mesType == messageTypes.MOVE:
                print("hareket eteceğizz")
                print(message)
                playerid = message["playerid"]

                if players[playerid]["timestamp"] > message["timestamp"]:
                    continue

                newX = message["X"]
                newY = message["Y"]
                # if players[playerid]["X"]==message
                players[playerid]["X"] = newX
                players[playerid]["Y"] = newY

                players[playerid]["timestamp"] = message["timestamp"]
                # TODO: implement
                # TODO: collision detection (player and food)
                # TODO: score update
                # todo: time update
                removeOfflineUsers()

                checkCollision(playerid)
                if(len(foods) < 100):
                    addFood(10)
                pass


def addFood(count=10):
    global foods
    for i in range(count):
        foods.append({
            "X": random.randrange(0, shared.MAP_WIDTH),
            "Y": random.randrange(0, shared.MAP_HEIGHT),
            "color": (random.randint(1, 255), random.randint(1, 255), random.randint(1, 255)),
            "size": random.randint(3, 10)
        })


def shrinkPlayers():
    global players
    while True:
        time.sleep(7)
        for id in players:
            if players[id]["score"] > 80:
                players[id]["score"] *= 0.95


thread1 = Thread(target=UDPsendStatus, args=(), daemon=True)


thread2_2 = Thread(target=messagegetterUDP, args=(), daemon=True)
thread0 = Thread(target=shrinkPlayers, args=(), daemon=True)

thread1.start()
# thread2_1.start()
thread2_2.start()
# thread3.start()
thread0.start()

while True:
    time.sleep(1)
