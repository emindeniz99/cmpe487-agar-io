from threading import Thread
import time
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
from xmlrpc.client import MAXINT
import pygame
import contextlib
with contextlib.redirect_stdout(None):
    import pygame
import random
import os

pygame.font.init()
NAME_FONT = pygame.font.SysFont("comicsans", 20)
TIME_FONT = pygame.font.SysFont("comicsans", 30)
SCORE_FONT = pygame.font.SysFont("comicsans", 26)

pygame.init()


class messageTypes(IntEnum):
    DISCOVER = 1
    DISCOVER_RESPONSE = 2
    JOIN_GAME = 3
    NEW_GAME_RESPONSE = 4
    MOVE = 5
    CURRENT_STATE = 6


serverIP = None
playerid = None

lastServerTimestamp = 0
gametime = 0
players = {
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

DISCO_PORT = 12345
MOVE_PORT = 12346
RECVSIZE = 204800

myName = "anon"

if len(sys.argv) > 1:
    myName = sys.argv[1]
else:
    myName = input("Write your name? ")


def disco():
    global players, serverIP

    while True:
        if serverIP != None:
            break
        DISCOVER_MESSAGE_BYTES = json.dumps(
            {"type": messageTypes.DISCOVER, "game": "agarip", "name": myName})
        DISCOVER_MESSAGE_BYTES = str.encode(DISCOVER_MESSAGE_BYTES)

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(("", 0))
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            for i in range(10):
                sock.sendto(DISCOVER_MESSAGE_BYTES,
                            ('<broadcast>', DISCO_PORT))
                # print("disco ")
        time.sleep(5)


def messagegetterTCP():
    # listener, get messages and print, also DISCOVER_RESPONSE

    global players, foods, serverIP, playerid
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", DISCO_PORT))
        s.listen()
        while True:
            # Start listenning
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            conn, addr = s.accept()
            sender = addr[0]  # ip
            with conn:
                output = conn.recv(RECVSIZE)
                output = output.decode('utf-8')
                # print(output, sender)
                # Parse the message
                message = json.loads(output)
                mes_type = message["type"]
                # Received message is type of "Discover Response"
                if mes_type == messageTypes.DISCOVER_RESPONSE:
                    # if message["IP"] == myIP:
                    #     continue
                    # print(message)
                    serverIP = sender
                    playerid = message["playerid"]


def messagegetterUDP():

    global players, foods, playerid, lastServerTimestamp, gametime

    # listener, get messages and print, also DISCOVER_RESPONSE
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("", MOVE_PORT))
        s.setblocking(0)
        while True:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            result = select.select([s], [], [])
            msg, address = result[0][0].recvfrom(RECVSIZE)
            # print("addd", address[0])
            sender = address[0]
            # print("SENDER:: ", sender)
            # print(msg)
            message = json.loads(msg.decode('utf-8'))
            mesType = message["type"]
            if mesType == messageTypes.CURRENT_STATE:
                # return discovery response
                # print("CURRENT_STATE")

                if lastServerTimestamp > message["timestamp"]:
                    continue

                # print(message)
                # for p in message["players"]:
                #     players[p]=message["players"][p]

                backupMe = players.get(
                    playerid) or message["players"].get(playerid)
                players = message["players"]
                if backupMe != None and ((message["players"][playerid].get("score")) >= (backupMe.get("score") or 0)):
                    players[playerid]["X"] = backupMe["X"]
                    players[playerid]["Y"] = backupMe["Y"]

                foods = message["foods"]

                lastServerTimestamp = message["timestamp"]
                gametime = message["gametime"]
                # if str(sender) == myIP:
                #     continue
                # players[newPlayerID] = newPlayer

                # sssss = (json.dumps(
                #     {"type": messageTypes.DISCOVER_RESPONSE,
                #      "playerid": newPlayerID,
                #      "players": players,
                #      "foods": foods
                #      }))
                # print(sssss)


def redraw_window():
    """
    draws each frame
    """
    WIN.fill((255, 255, 255))  # fill screen white, to clear old frames

    # draw all the orbs/balls
    for food in foods:
        print(food)
        pygame.draw.circle(WIN, food["color"],
                           (food["X"], food["Y"]), food["size"])

    # draw each player in the list
    for player in sorted(players, key=lambda x: players[x]["score"]):
        p = players[player]
        pygame.draw.circle(WIN, p["color"], (p["X"], p["Y"]),
                           round(math.sqrt(p["score"])))
        # render and draw name for each player
        text = NAME_FONT.render(p["name"], 1, (0, 0, 0))
        WIN.blit(text, (p["X"] - text.get_width() /
                 2, p["Y"] - text.get_height()/2))

    # draw scoreboard
    sort_players = list(
        reversed(sorted(players, key=lambda x: players[x]["score"])))
    title = TIME_FONT.render("Scoreboard", 1, (0, 0, 0))
    start_y = 25
    x = MAP_WIDTH - title.get_width() - 10
    WIN.blit(title, (x, 5))

    ran = min(len(players), 3)
    for count, i in enumerate(sort_players[:ran]):
        text = SCORE_FONT.render(
            str(count+1) + ". " + str(players[i]["name"]) + " "+str(players[i]["score"]), 1, (0, 0, 0))
        WIN.blit(text, (x, start_y + count * 20))

    # draw time
    text = TIME_FONT.render("Time: "+str(gametime//(10**6)), 1, (0, 0, 0))
    WIN.blit(text, (10, 10))
    # draw score
    text = TIME_FONT.render(
        "Score: " + str(round(players[playerid]["score"])), 1, (0, 0, 0))
    WIN.blit(text, (10, 15 + text.get_height()))


def main():
    global players, foods, serverIP, playerid
    # setup the clock, limit to 30fps
    while serverIP == None:
        time.sleep(0.01)
        continue
    clock = pygame.time.Clock()
    run = True

    while run:
        clock.tick(60)  # 60 fps max
        player = players.get(playerid)

        if not player:
            redraw_window()
            pygame.display.update()
            continue

        vel = 6 - round(math.sqrt(player["score"])/14)
        if vel <= 1:
            vel = 1

        # print(foods, players)
        # get key presses
        keys = pygame.key.get_pressed()
        # newX = player["X"]
        # newY = player["Y"]
        # movement based on key presses
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            if player["X"] - vel - 10 - player["score"] >= 0:
                player["X"] = player["X"] - vel

        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            if player["X"] + vel + 10 + player["score"] <= MAP_WIDTH:
                player["X"] = player["X"] + vel

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            if player["Y"] - vel - 10 - player["score"] >= 0:
                player["Y"] = player["Y"] - vel

        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            if player["Y"] + vel + 10 + player["score"] <= MAP_HEIGHT:
                player["Y"] = player["Y"] + vel

        moveMessage(player["X"], player["Y"])

        for event in pygame.event.get():
            # if user hits red x button close window
            if event.type == pygame.QUIT:
                run = False

            if event.type == pygame.KEYDOWN:
                # if user hits a escape key close program
                if event.key == pygame.K_ESCAPE:
                    run = False

        # redraw window then update the frame
        redraw_window()
        pygame.display.update()


def moveMessage(x, y):
    global players, foods, serverIP, playerid

    MOVE_MESSAGE_BYTES = json.dumps(
        {"type": messageTypes.MOVE, "playerid": playerid, "X": x, "Y": y, "timestamp": time.time_ns()})
    # print(MOVE_MESSAGE_BYTES)
    MOVE_MESSAGE_BYTES = str.encode(MOVE_MESSAGE_BYTES)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("", 0))
        for i in range(2):
            sock.sendto(MOVE_MESSAGE_BYTES,
                        (serverIP, DISCO_PORT))


thread3 = Thread(target=disco, args=(), daemon=True)
thread3.start()
thread4 = Thread(target=messagegetterTCP, args=(), daemon=True)
thread4.start()
thread5 = Thread(target=messagegetterUDP, args=(), daemon=True)
thread5.start()

# setup pygame window
MAP_WIDTH = 800  # x
MAP_HEIGHT = 500  # y

WIN = pygame.display.set_mode((MAP_WIDTH, MAP_HEIGHT))
pygame.display.set_caption("Blobs")

main()
