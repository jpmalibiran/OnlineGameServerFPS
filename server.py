"""
Author: Joseph Malibiran
Last Modified: October 20, 2020
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

#Connected users dictionary
clients = {}

#Network message queue
msgQueue = queue.Queue() 

#Lobby structures
lobbies = {} 
lobbyQueue = queue.Queue() #Queue of lobbies
playerLobbyQueue = queue.Queue() #Queue of players trying to join a match lobby
initialLobbyKey = 0
lobbyKeyCounter = 0


acceptedClientVersion = 'v0.1.0 indev'

verboseDebug = False

# Connection loop continuously listens for messages and stores them in a queue to be processed separately
def connectionLoop(sock):
   global msgQueue

   while True:
      data, addr = sock.recvfrom(1024)
      #data = str(data)

      msgDict = json.loads(data) # Convert [string json] to [python dictionary] 
      msgDict['ip'] = str(addr[0]) # Append 'ip' and 'source', the address of message sender, to python dictionary
      msgDict['port'] = str(addr[1])
      msgString = json.dumps(msgDict) # Convert new dictionary back into string
      #msgQueue.append(msgString) # Append new string to message queue to be processed later
      msgQueue.put(msgString)

# Process network messages that were accepted in connectionLoop() and stored in msgQueue
def processMessages(sock):
   global clients
   global msgQueue
   global acceptedClientVersion

   while True:

      if msgQueue.empty() == False:
         msgDict = json.loads(msgQueue.get()) # Note: msgQueue.get() is pop; removes foremost item and returns it.
         srcAddress = msgDict['ip'] + ":"  + msgDict['port']

         if msgDict['flag'] == 1: # New Client Connection
            if msgDict['message'] == acceptedClientVersion:
               clients[srcAddress] = {}
               clients[srcAddress]['lastPong'] = datetime.now()
               clients[srcAddress]['ip'] = str(msgDict['ip'])
               clients[srcAddress]['port'] = str(msgDict['port'])
               clients[srcAddress]['position'] = {"x": 0,"y": 0,"z": 0}
               clients[srcAddress]['orientation'] = {"yaw": 0,"pitch": 0}
               print('[Notice] New client connected: ', str(srcAddress))
            else:
               sendFlagMsg(sock, msgDict['ip'], msgDict['port'], 8) # Tells client it has an invalid version
               print('[Notice] Client failed to connect due to invalid version. ', msgDict['ip'] + ":"  + msgDict['port'])
         elif msgDict['flag'] == 4: # Client Pong
            print('[Routine] Received client pong from: ', srcAddress)

            if srcAddress in clients:
               clients[srcAddress]['lastPong'] = datetime.now()
            else:
               print('[Error] Client ping has invalid client address key! Aborting proceedure...')
         elif msgDict['flag'] == 9: # Matchmaking queue request
            print('[Notice] Received matchmaking request from: ', srcAddress)
            if srcAddress in clients:
               print('[Notice] Client placed in matchmaking queue: ', srcAddress)
               playerLobbyQueue.put(srcAddress)
            else:
               print('[Warning] Client not connected; Cannot process matchmaking.')

#This thread focuses on jobs that will execute every 2 seconds. 
def slowRoutines(sock):
   while True:
      routinePing(sock) #Pings every connected client; we expect a Pong message response from each of them. 
      routinePongCheck() #If it has been too long since the last Pong response consider that client disconnected and clean up references in the server as well as connected clients
      
      processMatchmaking() 

      time.sleep(2)

#TODO This thread focuses on jobs that will execute 30 times a seconds
def fastRoutines(sock):
   while True:
      print('')
      
      time.sleep(0.033)

#Sends a message to client at provided address containing provided flag
def sendFlagMsg(sock, targetIP, targetPort, flagType):
   global clients_lock

   print('[Routine] Sending flag to client ', targetIP + ":" + targetPort)

   flagDict = {}
   flagDict['flag'] = flagType 
   flagMsg = json.dumps(flagDict)

   clients_lock.acquire()
   sock.sendto(bytes(flagMsg,'utf8'), (targetIP, int(targetPort)))
   clients_lock.release()

#Pings every connected client
def routinePing(sock):
   global clients_lock

   if len(clients) <= 0:
      return

   print('[Routine] Pinging clients...')

   flagDict = {}
   flagDict['flag'] = 3 
   pingMsg = json.dumps(flagDict)
   clients_lock.acquire()

   for clientKey in clients:
      sock.sendto(bytes(pingMsg,'utf8'), (clients[clientKey]['ip'],int(clients[clientKey]['port'])))
      print(' - Pinging client: ', clientKey)

   clients_lock.release()

#Every Ping message to a client initiates a Pong message response to the server. 
#If it has been too long since the last Pong response consider that client disconnected and clean up references in the server as well as connected clients
def routinePongCheck():
   global clients_lock

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

def processMatchmaking():
   global lobbies
   global lobbyQueue
   global playerLobbyQueue
   global initialLobbyKey
   findLobbyForPlayer = True
   createNewLobby = False

   while playerLobbyQueue.empty() == False: # Go through all players in queue. TODO Note: potential issue of stalling here if there are an enormous amount of people waiting to join a lobby in a span of two seconds
      clientKey = playerLobbyQueue.get() # Pop player
      
      while findLobbyForPlayer:
         if initialLobbyKey != 0: # If there is a lobby being processed 
            if initialLobbyKey in lobbies:
               if lobbies[initialLobbyKey]['minPlayers'] < lobbies[initialLobbyKey]['maxPlayers']: # Lobby has space
                  print('[Notice] Adding player to lobby ', clientKey)
                  lobbies[initialLobbyKey].append(clientKey) # Add player to lobby
                  findLobbyForPlayer = False # break while loop
               elif lobbies[initialLobbyKey]['minPlayers'] >= lobbies[initialLobbyKey]['maxPlayers']: # Lobby is full
                  if lobbyQueue.empty() == False:
                     print('[Debug] Loading next lobby...')
                     initialLobbyKey = lobbyQueue.get() #load next lobby
                     #continue loop
                  elif lobbyQueue.empty() == True:
                     #create lobby
                     createNewLobby = True #create new lobby
                     findLobbyForPlayer = False # break while loop
            else:
               print('[Error] Invalid lobby key!')
               if lobbyQueue.empty() == False:
                  print('[Debug] Loading next lobby...')
                  initialLobbyKey = lobbyQueue.get() #load next lobby
                  #continue loop
               elif lobbyQueue.empty() == True:
                  #create lobby
                  createNewLobby = True #create new lobby
                  findLobbyForPlayer = False # break while loop
         elif initialLobbyKey == 0:
            if lobbyQueue.empty() == False:
               print('[Debug] Loading next lobby...')
               initialLobbyKey = lobbyQueue.get() #load next lobby
               #continue loop
            elif lobbyQueue.empty() == True:
               #create lobby
               createNewLobby = True #create new lobby
               findLobbyForPlayer = False # break while loop

      findLobbyForPlayer = True

      if createNewLobby == True:
         createNewLobby = False
         #create lobby
         print('[Notice] Creating new lobby with host ', clientKey)
         newlobbyKey = getNewLobbyIndex()
         lobbies[newlobbyKey] = {} # New lobby
         lobbies[newlobbyKey]['minPlayers'] = 2
         lobbies[newlobbyKey]['maxPlayers'] = 8
         lobbies[newlobbyKey]['host'] = clientKey # Person who can change lobby settings; Not server host
         lobbies[newlobbyKey]['players'] = {}
         lobbies[newlobbyKey]['players'].append(clientKey) # Add player to lobby
         lobbyQueue.put(newlobbyKey) # put new lobby in queue
         
#TODO
def updateClientsOnDisconnect():
   print('')

def getNewLobbyIndex():
   global lobbyKeyCounter
   lobbyKeyCounter = lobbyKeyCounter + 1

   if lobbyKeyCounter > 65530:
      lobbyKeyCounter = 1
   return lobbyKeyCounter

def main():
   print('[Notice] Setting up server... ')
   port = 12345
   s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   s.bind(('', port))
   #start_new_thread(fastRoutines, (s,))
   start_new_thread(connectionLoop, (s,))
   start_new_thread(processMessages, (s,))
   start_new_thread(slowRoutines, (s,))
   print('[Notice] Server running.')
   while True:
      time.sleep(1)

if __name__ == '__main__':
   main()
