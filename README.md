# Agar.io Clone - PyGame and UDP

![image](https://user-images.githubusercontent.com/44745432/150681267-4a9af117-64d9-4078-b087-31b96e96d321.png)

![image](https://user-images.githubusercontent.com/44745432/150681544-6367b137-8ba7-480b-9fc0-65045ff54459.png)

## How to Run

- Server should be running on one computer.  
  `python3 backend.py`
- Clients should be connected to same LAN. The client app discovers the server automatically.  
  `python3 frontend.py`

## Objectives

- Agar.io clone
- To make the game more competitive, adding some challenges like reducing the player mass
- Real-time gaming experience with low latency
- Preventing glitch in player movements

## Challenges

### TCP

- TCP packets increases the network load.
- This reduces experience of real-time gaming as number of players increases.
- So, we decided to use UDP.

### UDP

#### Missing packets

- resolved:
- with timestamp for each packet in order to ignore old packets
- sending same packets more than once in order to reduce chances of missing packets

### Client App Real-time Experience

- Firstly, our server was the only global source of game state. User inputs are sent to the server directly and new state is calculated on the server and this new state is streamed to clients.
- At this case, server response was lagging behind the clients’ keyboard input due to the round trip time. This means that users could not see their position change immediately.
- To solve this problem, we separated the clients' own state from server state. So, users does not see any delay for their keyboard inputs.

## [Project Plan](./ProjectPlan.pdf)

#### We did pair programming so we didn't split tasks.

## Presentation

[![Watch the video](https://img.youtube.com/vi/obvlDiW4bDA/maxresdefault.jpg)](https://youtu.be/obvlDiW4bDA)

https://www.youtube.com/watch?v=obvlDiW4bDA
