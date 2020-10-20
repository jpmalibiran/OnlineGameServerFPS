"""
Author: Joseph Malibiran
Last Modified: October 14, 2020
"""


import random
import socket
import time
from _thread import *
import threading
from datetime import datetime
import json
import queue

clients_lock = threading.Lock()
connected = 0

#Dictionary
clients = {}

#Queue
msgQueue = queue.Queue() 

# Connection loop continuously listens for messages and stores them in a queue to be processed separately
def connectionLoop(sock):
   while True:
      data, addr = sock.recvfrom(1024)
      #data = str(data)

      msgDict = json.loads(data) # Convert [string json] to [python dictionary] 
      msgDict['ip'] = str(addr[0]) # Append 'ip' and 'source', the address of message sender, to python dictionary
      msgDict['port'] = str(addr[1])
      msgString = json.dumps(msgDict) # Convert new dictionary back into string
      #msgQueue.append(msgString) # Append new string to message queue to be processed later
      msgQueue.put(msgString)

def processMessages(sock):

   while True:

      if msgQueue.empty() == False:
         msgDict = json.loads(msgQueue.get())

         if msgDict['flag'] == 1: # New Client Connection
            srcAddress = msgDict['ip'] + ":"  + msgDict['port']
            clients[srcAddress] = {}
            clients[srcAddress]['lastPong'] = datetime.now()
            clients[srcAddress]['ip'] = str(msgDict['ip'])
            clients[srcAddress]['port'] = str(msgDict['port'])
            clients[srcAddress]['position'] = {"x": 0,"y": 0,"z": 0}
            clients[srcAddress]['orientation'] = {"yaw": 0,"pitch": 0}
            print('[Notice] New client connected: ', str(srcAddress))

         elif msgDict['flag'] == 3: # Client Pong
            keyString = msgDict['ip'] + ":"  + msgDict['port']
            print('[Routine] Received client pong from: ', keyString)

            if keyString in clients:
               clients[keyString]['lastPong'] = datetime.now()
            else:
               print('[Error] Client ping has invalid client address key! Aborting proceedure...')


# Every loop, the server checks if a client has not sent a ping in the last 6 seconds. 
# If a client did not meet the pong conditions, the server drops the client from the game.
# If a client is dropped, the server sends a message to all clients currently connected to inform them of the dropped player. 
def cleanClients(sock):
   while True:
      routinePing(sock) #Pings every connected client; we expect a Pong message response from each of them. 
      routinePongCheck() #If it has been too long since the last Pong response consider that client disconnected and clean up references in the server as well as connected clients
            
      time.sleep(2)

# Every loop, the server updates the current state of the game. This game state contains the id’s and colours of all the players currently in the game.
# Every loop, the server sends a message containing the current state of the game. This game state contains the id’s and colours of all players currently in the game.
def gameLoop(sock):
   while True:
      print('')
      
      time.sleep(0.033)

#Pings every connected client
def routinePing(sock):

   if len(clients) <= 0:
      return

   print('[Routine] Pinging clients...')

   flagDict = {}
   flagDict['flag'] = 2 
   pingMsg = json.dumps(flagDict)
   clients_lock.acquire()

   for clientKey in clients:
      sock.sendto(bytes(pingMsg,'utf8'), (clients[clientKey]['ip'],int(clients[clientKey]['port'])))
      print(' - Pinging client: ', clientKey)

   clients_lock.release()

#Every Ping message to a client initiates a Pong message response to the server. 
#If it has been too long since the last Pong response consider that client disconnected and clean up references in the server as well as connected clients
def routinePongCheck():
   if len(clients) <= 0:
      return

   # Loop through clients
   for c in list(clients.keys()):

      # Every loop, the server checks if a client has not sent a pong in the last 6 seconds.
      if (datetime.now() - clients[c]['lastPong']).total_seconds() > 6:
         droppedClientIP = str(clients[c]['ip'])
         droppedClientPort = str(clients[c]['port'])
         dropedClientAddress = droppedClientIP + ":" + droppedClientPort
         # Drop the client from the game.
         print('[Notice] Dropped Client: ', droppedClientIP + ":" + droppedClientPort)
         clients_lock.acquire()
         del clients[dropedClientAddress]
         
         #Sends a message to all clients currently connected to inform them of the dropped player. 
         updateClientsOnDisconnect()
         #msgDict = {"cmd": 2,"player":{"ip":droppedClientIP, "port":droppedClientPort}}

         #msgJson = json.dumps(msgDict)
         #for targetClient in clients:
         #   sock.sendto(bytes(msgJson,'utf8'), (clients[targetClient]['ip'], int(clients[targetClient]['port']))) 

         clients_lock.release()

def updateClientsOnDisconnect():
   print('')

def main():
   print('[Notice] Setting up server... ')
   port = 12345
   s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   s.bind(('', port))
   #start_new_thread(gameLoop, (s,))
   start_new_thread(connectionLoop, (s,))
   start_new_thread(processMessages, (s,))
   start_new_thread(cleanClients, (s,))
   print('[Notice] Server running.')
   while True:
      time.sleep(1)

if __name__ == '__main__':
   main()
