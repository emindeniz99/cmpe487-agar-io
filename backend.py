from threading import Thread
import time
import json
import socket
import select
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
print("Welcome to agar.io clone server")


players = {
    'testuser1': {'X': 643, 'Y': 276, 'score': 100, 'color': (72, 131, 158), 'name': 'testuser', 'IP': '192.168.1.153', 'timestamp': 1942681807848047000}

    # playerid:{
    #   X
    #   Y
    #   score
    #   color
    #   name
    #   IP
    #   timestamp
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
    #   IP:userID
}

gameStartTime = time.time_ns()


def UDPsendStatus():
    global players, foods, gameStartTime, ipToIDmap
    # message sender, CHAT
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("", 0))
        while True:
            removeOfflineUsers()
            for playerID in players:
                player = players[playerID]
                if player["name"] == "testuser":
                    continue
                STATE_MESSAGE_BYTES = json.dumps(
                    {"type": shared.messageTypes.CURRENT_STATE,
                        "players": players,
                        "foods": foods,
                        "timestamp": time.time_ns(),
                        "gametime": (time.time_ns()-gameStartTime)//10**3
                     })
                STATE_MESSAGE_BYTES = str.encode(STATE_MESSAGE_BYTES)
                try:
                    for i in range(3):
                        sock.sendto(STATE_MESSAGE_BYTES,
                                    (player["IP"], shared.MOVE_PORT))
                except Exception as e:
                    # print("error",e)
                    pass
            time.sleep(0.01)


def checkCollision(playerid):
    global foods, players
    player = players[playerid]

    # check collison for foods and users
    for i, food in enumerate(foods[:]):
        dis = math.sqrt((player["X"] - food["X"]) **
                        2 + (player["Y"]-food["Y"])**2)
        if (math.sqrt(player["score"])) > dis:
            foods.remove(food)
            players[playerid]["score"] += food["size"]

    # check collisions between users
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
                # players[id]["timestamp"] += 10**8
                # players[id]["number_of_deaths"] += 1

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
                players[playerid]["timestamp"] += 10**8
                players[playerid]["number_of_deaths"] += 1


def removeOfflineUsers():
    """
    Remove the user that is offline for 5 seconds
    """
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

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("", shared.DISCO_PORT))
        s.setblocking(0)
        while True:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            result = select.select([s], [], [])
            msg, address = result[0][0].recvfrom(shared.RECVSIZE)
            # print("address", address[0])
            sender = address[0]
            # print("sender: ", sender)
            message = json.loads(msg.decode('utf-8'))
            mesType = message["type"]
            if mesType == shared.messageTypes.DISCOVER:
                # return discovery response
                # print(message)
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

                discovery_response = (json.dumps(
                    {"type": shared.messageTypes.DISCOVER_RESPONSE,
                     "playerid": newPlayerID,
                     "players": players,
                     "foods": foods
                     }))
                print(discovery_response)
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                        sock.connect((sender, shared.DISCO_PORT))
                        sock.sendall(discovery_response.encode('utf-8'))
                    ipToIDmap[message["name"]] = newPlayerID
                except Exception as e:
                    print("response  error: ", e)

            elif mesType == shared.messageTypes.MOVE:
                print("hareket eteceğizz")
                print(message)
                playerid = message["playerid"]

                # ignore old packets
                if players[playerid]["timestamp"] > message["timestamp"]:
                    continue

                newX = message["X"]
                newY = message["Y"]
                # if players[playerid]["X"]==message
                players[playerid]["X"] = newX
                players[playerid]["Y"] = newY

                players[playerid]["timestamp"] = message["timestamp"]

                removeOfflineUsers()

                # collision detection (player and food)
                checkCollision(playerid)

                # add new foods
                if(len(foods) < 100):
                    addFood(10)


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
        time.sleep(3)
        for id in players:
            if players[id]["score"] > 80:
                players[id]["score"] *= 0.95


thread_game_state_stream = Thread(target=UDPsendStatus, args=(), daemon=True)


thread_udp_listener = Thread(target=messagegetterUDP, args=(), daemon=True)
thread_shrink_player_score = Thread(target=shrinkPlayers, args=(), daemon=True)

thread_game_state_stream.start()
thread_udp_listener.start()
thread_shrink_player_score.start()

while True:
    time.sleep(1)
