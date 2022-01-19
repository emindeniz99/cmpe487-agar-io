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
import hashlib
import pyDes


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


myName = ""

if len(sys.argv) > 1:
    myName = sys.argv[1]
else:
    myName = input("Write your name? ")


myIP = get_ip()  # or "192.168.1.101"

print("Hello "+myName, ", IP: "+myIP)
print("Welcome to chat app")


class messageTypes(IntEnum):
    DISCOVER = 1
    DISCOVER_RESPONSE = 2
    CHAT = 3
    FILE = 4
    ACK = 5
    ENCRYPTIONDATA = 6


clients = {
    # name:ip
}

clientEncData = {
    # name:{
    #   p?
    #   g?
    #   A?
    #   B?
    #   key
    # }
}

# connected ip's
ipSet = set({})

PORT = 12345
CHUNK_SIZE = 1500
print("port=", PORT)

RECVSIZE = 20480


def listClients():
    # list Clients
    print("\n---")

    print("Clients")
    print("___<name> (<IP>)___")

    for k, v in clients.items():
        print(k, "\t(", v, ")")


counter = 0

sentfiles = {
    # ip: {
    #    packets:[{bytes:,
    #             sentTimeStamp:,
    #              #if delivered, delete the packet
    # }, {},{},....]
    #   do not use ----onFlyCount:x, // not logical, due to timestamp is related to this, its timestamp is old, it is not count as on fly
    #   RWND:1, initial value
    #   name: filename
    #   startTime:Time
    # }
}

deliveredFiles = {
    # ip:{
    #      packets:{} map
    # rwnd:10,
    # seqCount : counter
    # lastSeq : <= len(bytesArr)<chunksize
    # startTime:Time
    # }
}

encryptionInfo = {
    # ip:{
    #      p: int
    #      q: int
    #        myA:
    #        otherB:
    #
    # }
}


def primeGenerator():
    if random.random() > 0.5:
        return 5
    return 7


def encryptMessage(content, key):
    return pyDes.triple_des(str(key)[0:20].ljust(24)).encrypt((bytes(content, 'utf-8')), padmode=2)


def decryptMessage(content, key):
    return pyDes.triple_des(str(key)[0:20].ljust(24)).decrypt(eval(content), padmode=2).decode('utf-8')


def generateNewCipherKey(content, oldKey):
    result = hashlib.sha1((str(content)+str(oldKey)).encode())
    return result.hexdigest()


def onFlyCount(ip):
    fs = sentfiles[ip]
    count = 0
    for packet in fs["packets"]:
        if packet == None:  # delivered
            continue

        # Return the current time in seconds since the Epoch
        if (packet["sentTimeStamp"]+60) < int(time.time()):
            # old packet
            None
        else:
            count += 1
    return count


def allSent(ip):
    fs = sentfiles[ip]
    count = 0
    for packet in fs["packets"]:
        if packet != None:  # delivered
            count += 1
    return count == 0


def sendFileChunk(ip):
    fs = sentfiles[ip]
    remainingQuota = fs["RWND"] - onFlyCount(ip)
    # print("remainingQuota:", remainingQuota)
    index = 0
    while remainingQuota > 0 and index < len(fs["packets"]):
        if fs["packets"][index] == None:  # delivered
            index += 1
            continue
        packet = fs["packets"][index]
        if (packet["sentTimeStamp"]+60) < int(time.time()):
            if not sentfiles[ip].get("startTime"):
                sentfiles[ip]["startTime"] = time.time_ns()

            # send it
            FILE_MESSAGE_BYTES = json.dumps(
                {"type": messageTypes.FILE, "name": fs["name"], "body": list(packet["bytes"]), "seq": index+1})
            FILE_MESSAGE_BYTES = str.encode(FILE_MESSAGE_BYTES)

            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.bind(("", 0))
                sock.sendto(FILE_MESSAGE_BYTES, (ip, PORT))

            packet["sentTimeStamp"] = int(time.time())
            remainingQuota -= 1
        index += 1


def clientworker():
    # message sender, CHAT
    while True:
        global clients, ipSet, counter
        if len(clients.items()) == 0:
            counter = ((counter+1) % 3)
            print("\rNo Client Available, discovering ", "." *
                  counter, " "*(3-counter), end="")
            time.sleep(0.2)
            continue
        listClients()

        targetname = input("type name ( e.g 'emin' ) \n").strip()
        if(targetname == "quit"):
            sys.exit()
        if targetname == "":
            continue
        print("selected name: ", targetname,  clients.get(targetname))
        targetip = clients.get(targetname)
        if targetip:
            option = input("type 'file' or 'text'\n")
            if option.startswith("f"):
                # send file
                path = input("file path? relative or absolute ")
                arr = []
                with open(path, "rb") as f:
                    print(f.name)
                    byte = f.read(CHUNK_SIZE)
                    while byte:
                        arr.append(
                            {"bytes": byte, "sentTimeStamp": 0})
                        # Do stuff with byte.
                        byte = f.read(CHUNK_SIZE)
                    if len(arr[-1]["bytes"]) == CHUNK_SIZE:
                        arr.append({"bytes": b"", "sentTimeStamp": 0})
                    print("seq:# ", str(len(arr)))
                    # print(arr)
                filesize = (len(arr)-1)*CHUNK_SIZE + len(arr[-1]["bytes"])
                sentfiles[targetip] = {
                    "RWND": 1,
                    "name": f.name,
                    "packets": arr}
                while True:
                    sendFileChunk(targetip)
                    if allSent(targetip):
                        print("file is sent")

                        delta = (time.time_ns() -
                                 sentfiles[targetip].get("startTime"))
                        print("duration:", str(delta), "ns")
                        print("speed", filesize/delta, "byte/ns")
                        print("speed", (filesize/delta)*10**9, "byte/second")
                        print("speed", (filesize/delta)
                              * 10**3, "megabyte/second")
                        print("speed", (filesize/delta)
                              * 10**3 * 8, "megabit/second")
                        # reset sender Buffer
                        sentfiles[targetip] = None

                        break
                    # to resend no ACKed files and check the file sending
                    time.sleep(1)

            elif option.startswith("t"):
                # send message
                messageContent = input("type your message\n")
                print("message is encrypted with key: ",
                      clientEncData[targetname]["key"])
                # print(clientEncData)
                key = clientEncData[targetname]["key"]
                enc_mes = encryptMessage(messageContent, key)
                print("encrypted Message: ", str(enc_mes))

                req = json.dumps(
                    {"type": messageTypes.CHAT, "name": myName, "body": str(enc_mes)})

                print("message is sending...")
                sendTCPMessage(req, targetip)
                print("\rmessage is sent")
                newKey = generateNewCipherKey(messageContent, key)
                print("NewCipherKey: ", newKey)
                clientEncData[targetname]["key"] = newKey

        else:
            print("type someone who exists on list")


def sendTCPMessage(reqstring, ip):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((ip, PORT))
            sock.sendall(reqstring.encode('utf-8'))
    except Exception as e:
        print("response error: ", e)
        clients.pop(a)
        print("client is offline")


def messagegetterUDP():
    # listener, get messages and print, also DISCOVER_RESPONSE
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("", PORT))
        s.setblocking(0)
        while True:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            result = select.select([s], [], [])
            msg, address = result[0][0].recvfrom(RECVSIZE)
            # print("addd", address[0])
            sender = address[0]
            message = json.loads(msg.decode('utf-8'))
            mesType = message["type"]
            if mesType == messageTypes.DISCOVER:
                # return discovery response
                if message["IP"] == myIP:
                    continue
                if clients.get(message["name"]):
                    continue

                g = primeGenerator()
                p = primeGenerator()
                a = random.randint(1, 10**6)

                clients[message["name"]] = message["IP"]
                sssss = (json.dumps(
                    {"type": messageTypes.DISCOVER_RESPONSE,
                     "name": myName,
                     "IP": myIP,
                     "g": g,
                     "p": p,
                     "A": (g**a) % p,
                     }))
                if not clientEncData.get(message["name"]):
                    clientEncData[message["name"]] = {}

                clientEncData[message["name"]]["a"] = a
                clientEncData[message["name"]]["p"] = p

                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                        sock.connect((message["IP"], PORT))
                        sock.sendall(sssss.encode('utf-8'))
                    # print("sent, response")
                except Exception as e:
                    print("response  error: ", e)

            #  this block is deprecated
            # elif mesType == messageTypes.CHAT:
            #     print("\n-----")
            #     print("Sender: ", message["name"],
            #           clients.get(message["name"]))
            #     print("ENCMessage: ", message["body"])
            #     print(" KEY: ", clientEncData[message["name"]]["key"])
            #     key = clientEncData[message["name"]]["key"]
            #     dec_mes = decryptMessage(message["body"], key)
            #     print(dec_mes)
            #     print("Message: ", dec_mes)
            #     print("newKEY::: ", generateNewCipherKey(dec_mes, key))

            elif mesType == messageTypes.FILE:
                fileName = message["name"]
                body = message["body"]
                seq = message["seq"]
                RWNDVALUE = 10
                if deliveredFiles.get(sender) == None:
                    deliveredFiles[sender] = {
                        "packets": {}, "RWND": RWNDVALUE, "seqCount": 0, "startTime": time.time_ns()}

                if not deliveredFiles[sender]["packets"].get(seq):
                    deliveredFiles[sender]["seqCount"] += 1

                deliveredFiles[sender]["packets"][seq] = (
                    {"bytes": body, "seq": seq})
                deliveredFiles[sender]["name"] = fileName
                # print("deliveredFiles[sender]: ", deliveredFiles[sender])

                sssss = (json.dumps(
                    {"type": messageTypes.ACK, "seq": seq, "RWND": RWNDVALUE}))

                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                        sock.connect((sender, PORT))
                        sock.sendall(sssss.encode('utf-8'))
                    print("ACK#"+str(seq))
                    print("seqCount=", deliveredFiles[sender]["seqCount"])
                except Exception as e:
                    print("response  eorr: ", e)

                if len(body) < CHUNK_SIZE:
                    # sending finished

                    deliveredFiles[sender]["lastSeq"] = seq

                if deliveredFiles[sender].get("lastSeq") == deliveredFiles[sender]["seqCount"]:
                    # delivered!

                    myFile = []

                    for i in range(1, deliveredFiles[sender].get("lastSeq")+1):
                        myFile += deliveredFiles[sender]["packets"][i]["bytes"]
                    # print("myfile: ", myFile)

                    dirName = "files_" + \
                        getSenderName(sender)+"_"+str(int(time.time()))
                    print("dirName: ", dirName)
                    if not os.path.exists(dirName):
                        os.mkdir(dirName)
                        # print("Directory ", dirName,  " Created ")
                    with open(dirName+"/"+fileName, "wb") as f:
                        print(f.name)
                        byte = f.write(bytes(myFile))
                    delta = (time.time_ns() -
                             deliveredFiles[sender]["startTime"])
                    print("duration:", str(delta), "ns")
                    filesize = (deliveredFiles[sender].get(
                        "lastSeq")-1)*CHUNK_SIZE + len(deliveredFiles[sender]["packets"][deliveredFiles[sender].get("lastSeq")]["bytes"])
                    print("speed", filesize/delta, "byte/ns")
                    print("speed", (filesize/delta)*10**9, "byte/second")
                    print("speed", (filesize/delta)*10**3, "megabyte/second")
                    print("speed", (filesize/delta) *
                          10**3 * 8, "megabit/second")
                    # reset sender Buffer
                    deliveredFiles[sender] = None
            # print("incoming UDP: ", message)

            continue


def getSenderName(ip):
    for (k, v) in clients.items():
        if v == ip:
            return k


def messagegetterTCP():
    # listener, get messages and print, also DISCOVER_RESPONSE

    global clients
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", PORT))
        s.listen()
        while True:
            # Start listenning
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            conn, addr = s.accept()
            sender = addr[0]
            with conn:
                output = conn.recv(RECVSIZE)
                output = output.decode('utf-8')

                # Parse the message
                message = json.loads(output)
                mesType = message["type"]
                # Received message is type of "Discover Response"
                if mesType == messageTypes.DISCOVER_RESPONSE:
                    if message["IP"] == myIP:
                        continue

                    if clients.get(message["name"]):
                        continue
                    # Add responded user to the online users dictionary
                    clients[message["name"]] = message["IP"]
                    g = message["g"]
                    p = message["p"]
                    A = message["A"]
                    b = random.randint(1, 10**6)
                    B = (g**b) % p

                    sssss = (json.dumps(
                        {"type": messageTypes.ENCRYPTIONDATA,
                         "name": myName,
                         "IP": myIP,
                         "B": B
                         }))

                    try:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                            sock.connect((message["IP"], PORT))
                            sock.sendall(sssss.encode('utf-8'))
                        # print("sent, response")
                        # ADD ENCKEY
                        if not clientEncData.get(message["name"]):
                            clientEncData[message["name"]] = {}

                        clientEncData[message["name"]]["key"] = generateNewCipherKey(
                            "", (A**b) % p)

                        # print(clientEncData)
                    except Exception as e:
                        print("response  eorr: ", e)

                if mesType == messageTypes.ENCRYPTIONDATA:
                    # Add responded user to the online users dictionary
                    clients[message["name"]] = message["IP"]
                    B = message["B"]
                    p = clientEncData[message["name"]]["p"]
                    a = clientEncData[message["name"]]["a"]

                    clientEncData[message["name"]]["key"] = generateNewCipherKey(
                        "", (B**a) % p)
                    # print(clientEncData)
                # Received message is type of "Chat"
                elif mesType == messageTypes.CHAT:
                    # Print the message to the console
                    print("\n-----")
                    print("Sender: ", message["name"],
                          clients.get(message["name"]))
                    print("encrypted message: ", message["body"])
                    print("message is decrypted with key: ",
                          clientEncData[message["name"]]["key"])
                    key = clientEncData[message["name"]]["key"]
                    dec_mes = decryptMessage(message["body"], key)
                    print(dec_mes)
                    print("Message: ", dec_mes)
                    newKey = generateNewCipherKey(dec_mes, key)
                    print("NewCipherKey: ", newKey)
                    clientEncData[message["name"]]["key"] = newKey

                elif mesType == messageTypes.ACK:
                    # Print the message to the console
                    seq = message["seq"]
                    RWND = message["RWND"]
                    sentfiles[sender]["RWND"] = RWND
                    sentfiles[sender]["packets"][seq-1] = None
                    sendFileChunk(sender)
                # print("incoming TCP: ", message, )


def disco():
    while True:
        DISCOVER_MESSAGE_BYTES = json.dumps(
            {"type": messageTypes.DISCOVER, "name": myName, "IP": myIP})
        DISCOVER_MESSAGE_BYTES = str.encode(DISCOVER_MESSAGE_BYTES)

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(("", 0))
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            for i in range(10):
                sock.sendto(DISCOVER_MESSAGE_BYTES, ('<broadcast>', PORT))
                # print("disco ")
        time.sleep(5)


thread1 = Thread(target=clientworker, args=(), daemon=True)

thread2_1 = Thread(target=messagegetterTCP, args=())
thread2_1.daemon = True


thread2_2 = Thread(target=messagegetterUDP, args=(), daemon=True)

thread3 = Thread(target=disco, args=(), daemon=True)

thread1.start()
thread2_1.start()
thread2_2.start()
thread3.start()

while True:
    time.sleep(1)
