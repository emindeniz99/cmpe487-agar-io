from threading import Thread
import time
from threading import Thread
import time
import sys
import json
import socket
import select
import math
from xmlrpc.client import MAXINT
import pygame
import contextlib
with contextlib.redirect_stdout(None):
    import pygame
import shared


pygame.font.init()
NAME_FONT = pygame.font.SysFont("comicsans", 20)
TIME_FONT = pygame.font.SysFont("comicsans", 30)
SCORE_FONT = pygame.font.SysFont("comicsans", 26)

pygame.init()


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

myName = "anonim"

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
            {"type": shared.messageTypes.DISCOVER, "game": "agario-clone", "name": myName})
        DISCOVER_MESSAGE_BYTES = str.encode(DISCOVER_MESSAGE_BYTES)

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(("", 0))
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            for i in range(10):
                sock.sendto(DISCOVER_MESSAGE_BYTES,
                            ('<broadcast>', shared.DISCO_PORT))
        time.sleep(5)


def messagegetterTCP():
    #

    global players, foods, serverIP, playerid
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("", shared.DISCO_PORT))
        s.listen()
        while True:
            # Start listenning
            conn, addr = s.accept()
            sender = addr[0]  # ip
            with conn:
                output = conn.recv(shared.RECVSIZE)
                output = output.decode('utf-8')
                print(output, sender)
                # Parse the message
                message = json.loads(output)
                mes_type = message["type"]
                # Received message is type of "Discover Response"
                if mes_type == shared.messageTypes.DISCOVER_RESPONSE:
                    # if message["IP"] == myIP:
                    #     continue
                    # print(message)
                    serverIP = sender
                    playerid = message["playerid"]


def messagegetterUDP():

    global players, foods, playerid, lastServerTimestamp, gametime

    # listener, get messages and print, also DISCOVER_RESPONSE
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("", shared.MOVE_PORT))
        s.setblocking(0)
        while True:
            result = select.select([s], [], [])
            msg, address = result[0][0].recvfrom(shared.RECVSIZE)
            # print("addd", address[0])
            sender = address[0]
            # print("sender: ", sender)
            # print(msg)
            message = json.loads(msg.decode('utf-8'))
            mesType = message["type"]
            if mesType == shared.messageTypes.CURRENT_STATE:

                if lastServerTimestamp > message["timestamp"]:
                    continue

                localMe = players.get(
                    playerid)
                players = message["players"]
                if localMe != None and message["players"][playerid].get("number_of_deaths") == localMe.get("number_of_deaths"):
                    if ((message["players"][playerid].get("score")) >= (localMe.get("score"))):
                        players[playerid]["X"] = localMe["X"]
                        players[playerid]["Y"] = localMe["Y"]

                foods = message["foods"]

                lastServerTimestamp = message["timestamp"]
                gametime = message["gametime"]


def redraw_window():
    """
    draws new frame
    """
    WIN.fill((255, 255, 255))  # clear previous frame

    # draw all the foods
    for food in foods:
        print(food)
        pygame.draw.circle(WIN, food["color"],
                           (food["X"], food["Y"]), food["size"])

    # draw each player in the list
    for player in sorted(players, key=lambda x: players[x]["score"]):
        p = players[player]
        pygame.draw.circle(WIN, p["color"], (p["X"], p["Y"]),
                           math.sqrt(p["score"]))
        # render and draw name for each player
        text = NAME_FONT.render(p["name"], 1, (0, 0, 0))
        WIN.blit(text, (p["X"] - text.get_width() /
                 2, p["Y"] - text.get_height()/2))

    # draw scoreboard
    sort_players = list(
        reversed(sorted(players, key=lambda x: players[x]["score"])))
    title = TIME_FONT.render("Scoreboard", 1, (0, 0, 0))
    start_y = 25
    x = shared.MAP_WIDTH - title.get_width() - 10
    WIN.blit(title, (x, 5))

    ran = min(len(players), 3)
    for count, i in enumerate(sort_players[:ran]):
        text = SCORE_FONT.render(
            str(count+1) + ". " + str(players[i]["name"]) + " "+str(players[i]["score"]-shared.INITIAL_SCORE), 1, (0, 0, 0))
        WIN.blit(text, (x, start_y + count * 20))

    # draw gametime
    text = TIME_FONT.render("Time: "+str(gametime//(10**6)), 1, (0, 0, 0))
    WIN.blit(text, (10, 10))

    # draw score
    text = TIME_FONT.render(
        "Score: " + str(round(players[playerid]["score"]-shared.INITIAL_SCORE)), 1, (0, 0, 0))
    WIN.blit(text, (10, 15 + text.get_height()))


def getSizeFromScore(score):
    return math.sqrt(score)


def main():
    global players, foods, serverIP, playerid
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

        vel = 6 - round(math.sqrt(player["score"])/10)
        if vel <= 1:
            vel = 1

        # print(foods, players)
        # get key presses
        keys = pygame.key.get_pressed()

        # movement based on key presses
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            player["X"] = max(player["X"] - vel, 0 +
                              getSizeFromScore(player["score"]))

        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            player["X"] = min(player["X"] + vel, shared.MAP_WIDTH -
                              getSizeFromScore(player["score"]))

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            player["Y"] = max(player["Y"] - vel, 0 +
                              getSizeFromScore(player["score"]))

        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            player["Y"] = min(player["Y"] + vel, shared.MAP_HEIGHT -
                              getSizeFromScore(player["score"]))

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
        {"type": shared.messageTypes.MOVE, "playerid": playerid, "X": x, "Y": y, "timestamp": time.time_ns()})
    # print(MOVE_MESSAGE_BYTES)
    MOVE_MESSAGE_BYTES = str.encode(MOVE_MESSAGE_BYTES)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("", 0))
        for i in range(2):
            sock.sendto(MOVE_MESSAGE_BYTES,
                        (serverIP, shared.DISCO_PORT))


thread_discovery = Thread(target=disco, args=(), daemon=True)
thread_discovery.start()
thread_TCP_listener = Thread(target=messagegetterTCP, args=(), daemon=True)
thread_TCP_listener.start()
thread_UDP_listener = Thread(target=messagegetterUDP, args=(), daemon=True)
thread_UDP_listener.start()

# setup pygame window
WIN = pygame.display.set_mode((shared.MAP_WIDTH, shared.MAP_HEIGHT))
pygame.display.set_caption("agar.io clone")

main()
