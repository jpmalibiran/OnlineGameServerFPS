"""
Author: Joseph Malibiran
Last Modified: December 9, 2020
"""

import random
import socket
import time
from _thread import *
import threading
from datetime import datetime
import json
import queue

import auth as serverAuth
import matchmaking as mmScr
import gameplay as gameScr

class Server:

   def __init__(self):
      print('[Notice] Creating server instance: ')
      print('    Initializing server instance attributes...')
      self.clients_lock = threading.Lock()
      #self.connected = 0

      #Connected users dictionary
      self.clients = {}
      self.clientIDCounter = 0 # ID assigned to concurrent users, not profile ID

      #Network message queue
      self.msgQueue = queue.Queue() 

      #Accepted Client Version
      self.acceptedClientVersion = 'v0.1.1 indev'

      #Debug Settings
      self.verboseDebug = False

      #Server Settings
      self.port = 12345
      self.secondsBeforeClientTimeout = 6
      self.keepServerRunning = True
      self.maintainConnectionLoop = True
      self.maintainProcessMessagesThread = True

      self.isServerRunning = False
      self.isConnectionLoopRunning = False
      self.isProcessMessagesRunning = False
      self.isServerReady = False

      #Server objects
      self.matchMakingObj = mmScr.Matchmaking(self)
      self.gameScr = gameScr.Gameplay(self, self.matchMakingObj)

      #Socket
      print('    Setting up socket... ')
      self.moduleSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      self.moduleSock.bind(('', self.port))

   # Sets up server threads
   def launchServer(self):

      if self.isServerRunning == True:
         print('[Warning] Server already running.')
         return

      self.keepServerRunning = True
      self.isServerRunning = True

      print('[Notice] Launching server: ')
      
      #newSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      #newSock.bind(('', self.port))

      #start_new_thread(fastRoutines, (s,))
      start_new_thread(self.connectionLoop, (self.moduleSock,))
      start_new_thread(self.processMessages, (self.moduleSock,))
      start_new_thread(self.slowRoutines, (self.moduleSock,))

      time.sleep(0.4)
      self.CheckServerReady()

      while self.keepServerRunning:
         time.sleep(1)
      
      self.isServerRunning = False
      print('[Notice] Server terminated.')

   # Connection loop continuously listens for messages and stores them in a queue to be processed separately
   def connectionLoop(self, sock):
      #global msgQueue
      self.maintainConnectionLoop = True
      self.isConnectionLoopRunning = True

      print('    Starting [connectionLoop] thread...')

      while self.maintainConnectionLoop:
         data, addr = sock.recvfrom(1024)
         #data = str(data)

         msgDict = json.loads(data) # Convert [string json] to [python dictionary] 
         msgDict['ip'] = str(addr[0]) # Append 'ip' and 'source', the address of message sender, to python dictionary
         msgDict['port'] = str(addr[1])
         msgString = json.dumps(msgDict) # Convert new dictionary back into string
         self.msgQueue.put(msgString) #Queue new string to message queue to be processed later

   # Process network messages that were accepted in connectionLoop() and stored in msgQueue
   def processMessages(self, sock):
      self.maintainProcessMessagesThread = True
      self.isProcessMessagesRunning = True

      print('    Starting [processMessages] thread...')

      while self.maintainProcessMessagesThread:
         if self.msgQueue.empty() == False:
            msgDict = json.loads(self.msgQueue.get()) # Note: msgQueue.get() is pop; removes foremost item and returns it.
            srcAddress = msgDict['ip'] + ":"  + msgDict['port']

            if msgDict['flag'] == 1: # New Client Connection. 
               if msgDict['version'] == self.acceptedClientVersion:
                  print('[Notice] New client connected: ', str(srcAddress))
                  self.sendFlagMsg(msgDict['ip'], msgDict['port'], 1) # Tells client it has mutual connection established
               else:
                  self.sendFlagMsg(msgDict['ip'], msgDict['port'], 8) # Tells client it has an invalid version
                  print('[Notice] Client failed to connect due to invalid version. ', msgDict['ip'] + ":"  + msgDict['port'])
            elif msgDict['flag'] == 4: # Client Pong
               if self.verboseDebug:
                  print('[Routine] Received client pong from: ', srcAddress)
               
               if srcAddress in self.clients:
                  self.clients[srcAddress]['lastPong'] = datetime.now()
               else:
                  print('[Error] Client ping has invalid client address key! Aborting proceedure...')
            elif msgDict['flag'] == 12: # Client Login
               if self.checkVersion(msgDict['version']):
                  print('[Notice] Received login attempt from: ', srcAddress)
                  if serverAuth.loginAccount(msgDict['username'], msgDict['password']) == True:
                     self.clients[srcAddress] = {}
                     self.clients[srcAddress]['lastPong'] = datetime.now()
                     self.clients[srcAddress]['username'] = msgDict['username']
                     self.clients[srcAddress]['mmr'] = 1500
                     self.clients[srcAddress]['ip'] = str(msgDict['ip'])
                     self.clients[srcAddress]['port'] = str(msgDict['port'])
                     self.clients[srcAddress]['initialLobby'] = 0
                     #self.clients[srcAddress]['position'] = {"x": 0,"y": 0,"z": 0}
                     #self.clients[srcAddress]['orientation'] = {"yaw": 0,"pitch": 0}
                     #self.clients[srcAddress]['latency'] = 0
                     #self.clients[srcAddress]['health'] = 100
                     self.sendFlagMsg(msgDict['ip'], msgDict['port'], 12) # Tells client it has logged in successfully
                     print('[Notice] Client logged in as ' + msgDict['username'] + '.')
                  else:
                     self.sendFlagMsg(msgDict['ip'], msgDict['port'], 15) # Tells client login has failed
                     print('[Notice] Client  ' + srcAddress + ' failed to log in.')
               else:
                  self.sendFlagMsg(msgDict['ip'], msgDict['port'], 8) # Tells client it has an invalid version
                  print('[Notice] Client failed to connect due to invalid version. ', msgDict['ip'] + ":"  + msgDict['port'])
            elif msgDict['flag'] == 11: # Account registration
               if self.checkVersion(msgDict['version']):
                  print('[Notice] Received registration attempt from: ', srcAddress)
                  if serverAuth.createAccount(msgDict['username'], msgDict['password']) == True:
                     self.sendFlagMsg(msgDict['ip'], msgDict['port'], 11) # Tells client it has registered successfully
                     print('[Notice] Client registered account: ', msgDict['username'])
                  else:
                     self.sendFlagMsg(msgDict['ip'], msgDict['port'], 14) # Tells client registration has failed
                     print('[Notice] Client  ' + srcAddress + ' failed to register account.')
               else:
                  self.sendFlagMsg(msgDict['ip'], msgDict['port'], 8) # Tells client it has an invalid version
                  print('[Notice] Client failed to connect due to invalid version. ', msgDict['ip'] + ":"  + msgDict['port'])
            elif msgDict['flag'] == 9: # Queue Matchmaking
               print('[Notice] Received matchmaking queue request from: ', srcAddress)
               if srcAddress in self.clients:
                  self.matchMakingObj.addPlayerToQueue(srcAddress, 1500) #Add player to matchmaking queue
                  self.sendFlagMsg(msgDict['ip'], msgDict['port'], 9) # Tells client it has joined matchmaking queue
               else:
                  self.sendFlagMsg(msgDict['ip'], msgDict['port'], 17) # Tells client it has failed to join matchmaking queue
            elif msgDict['flag'] == 10: # leave Matchmaking
               if srcAddress in self.clients:
                  self.removePlayerFromQueueOrLobby(srcAddress)
                  self.sendFlagMsg(msgDict['ip'], msgDict['port'], 10) # Tells client they have left the lobby
            elif msgDict['flag'] == 13: # profile info request
               if srcAddress in self.clients:
                  self.fetchProfileData(msgDict['username'], srcAddress)
               else:
                  self.sendFlagMsg(msgDict['ip'], msgDict['port'], 16) # Tells client failed to fetch profile data
                  

   #This thread focuses on jobs that will execute every 2 seconds. 
   def slowRoutines(self, sock):
      while True:

         if self.isServerReady:
            self.routinePing(sock) #Pings every connected client; we expect a Pong message response from each of them. 
            self.routinePongCheck(sock) #If it has been too long since the last Pong response consider that client disconnected and clean up references in the server as well as connected clients

            self.matchMakingObj.sortQueuedPlayers()

            #Subtract 2 seconds from the matchmaking coundown timer every loop. If the countdown reaches 0 create a lobby with the currently queued players.
            if self.matchMakingObj.countdownTimer(-2):
               print('[Notice] Matchmaking Commenced.')
               self.matchMakingObj.startFullLobbies()

         time.sleep(2)

   #Sends a message to client at provided address containing provided flag
   def sendFlagMsg(self, targetIP, targetPort, flagType):
      if self.verboseDebug:
         print('[Routine] Sending flag to client ', targetIP + ":" + targetPort)

      flagDict = {}
      flagDict['flag'] = flagType 
      flagMsg = json.dumps(flagDict)

      self.clients_lock.acquire()
      self.moduleSock.sendto(bytes(flagMsg,'utf8'), (targetIP, int(targetPort)))
      self.clients_lock.release()
   
   #Sends a message to all connected clients
   def sendMsgToAll(self, msg: str):
      if self.verboseDebug:
         print('[Routine] Sending message to all connected clients.')
      
      self.clients_lock.acquire()
      for clientAddress in self.clients:
         self.moduleSock.sendto(bytes(msg,'utf8'), (self.clients[clientAddress]['ip'], int(self.clients[clientAddress]['port'])))
      self.clients_lock.release()

   #Sends a message to every client in a specified lobby
   def sendMsgToLobby(self, msg: str, lobby: int):
      if lobby == 0:
         return
      if self.verboseDebug:
         print('[Routine] Sending message to lobby #' + str(lobby))
      
      clientList = self.matchMakingObj.getLobbyPlayers(lobby)
      self.clients_lock.acquire()
      for clientAddress in clientList:
         self.moduleSock.sendto(bytes(msg,'utf8'), (self.clients[clientAddress]['ip'], int(self.clients[clientAddress]['port'])))
      self.clients_lock.release()

   #Checks if the server is ready.
   def CheckServerReady(self):
      if self.isServerRunning == True and self.isConnectionLoopRunning == True and self.isProcessMessagesRunning == True:
         self.isServerReady = True
         print('[Notice] Server running.')
      else:
         self.isServerReady = False
      return self.isServerReady

   #TODO make this error proof
   def getNewClientID(self):
      self.clientIDCounter = self.clientIDCounter + 1

      if self.clientIDCounter > 65530:
         self.clientIDCounter = 1
      return self.clientIDCounter

   #Pings every connected client
   def routinePing(self,sock):

      if len(self.clients) <= 0:
         return

      if self.verboseDebug:
         print('[Routine] Pinging clients...')

      flagDict = {}
      flagDict['flag'] = 3 
      pingMsg = json.dumps(flagDict)
      self.clients_lock.acquire()

      for clientKey in self.clients:
         sock.sendto(bytes(pingMsg,'utf8'), (self.clients[clientKey]['ip'],int(self.clients[clientKey]['port'])))
         if self.verboseDebug:
            print(' - Pinging client: ', clientKey)

      self.clients_lock.release()

   #Every Ping message to a client initiates a Pong message response to the server. 
   #If it has been too long since the last Pong response consider that client disconnected and clean up references in the server as well as connected clients
   def routinePongCheck(self, sock):
      if len(self.clients) <= 0:
         return

      # Loop through clients
      for c in list(self.clients.keys()):

         # Every loop, the server checks if a client has not sent a pong in the last self.secondsBeforeClientTimeout seconds.
         if (datetime.now() - self.clients[c]['lastPong']).total_seconds() > self.secondsBeforeClientTimeout:
            droppedClientIP = str(self.clients[c]['ip'])
            droppedClientPort = str(self.clients[c]['port'])
            dropedClientAddress = droppedClientIP + ":" + droppedClientPort
            # Drop the client from the game.
            
            self.clients_lock.acquire()

            #delete player from lobby if applicable TODO untested
            #removePlayerFromLobby(sock, dropedClientAddress)
            self.disconnectClient(dropedClientAddress)
            print('[Notice] Dropped Client: ', droppedClientIP + ":" + droppedClientPort)

            #del self.clients[dropedClientAddress]
            
            #TODO Sends a message to all clients currently connected to inform them of the dropped player. 
            #updateClientsOnDisconnect()
            #msgDict = {"cmd": 2,"player":{"ip":droppedClientIP, "port":droppedClientPort}}

            #msgJson = json.dumps(msgDict)
            #for targetClient in clients:
            #   sock.sendto(bytes(msgJson,'utf8'), (clients[targetClient]['ip'], int(clients[targetClient]['port']))) 

            self.clients_lock.release()

   #Check if received version is the proper accepted version by the server
   def checkVersion(self, receivedClientVersion):
      if receivedClientVersion == self.acceptedClientVersion:
         return True
      return False

   def setPlayerCurrentLobby(self, address: str, lobbyKey: int):
      if address in self.clients:
         self.clients[address]['initialLobby'] = lobbyKey
         return True
      return False

   def removePlayerFromQueueOrLobby(self, address: str):
      if address in self.clients:
         if self.clients[address]['initialLobby'] == 0:
            self.matchMakingObj.removePlayerFromQueue(address)
            print('[Notice] Removed player ' + address + ' from matchmaking queue.')
         else:
            self.matchMakingObj.removePlayerFromLobby(address, self.clients[address]['initialLobby'])
            print('[Notice] Removed player ' + address + ' from lobby #' + self.clients[address]['initialLobby'])
      else:
         print('[Warning] Target client is not logged in; aborting operation...')

   def fetchProfileData(self, targetAddress, receiverAddress):
      if receiverAddress in self.clients:
         fetchData = serverAuth.lookupAccount(self.clients[targetAddress]['username'])

         if 'username' in fetchData:
            if fetchData['username'] == 'n/a':
               print('[Warning] Target client data not found.')
               self.sendFlagMsg(self.clients[receiverAddress]['ip'], int(self.clients[receiverAddress]['port']), 16) # Tells client failed to fetch profile data
               return False
         else:
            print('[Warning] Target client data not found.')
            self.sendFlagMsg(self.clients[receiverAddress]['ip'], int(self.clients[receiverAddress]['port']), 16) # Tells client failed to fetch profile data
            return False

         if 'username' in fetchData and 'mmr' in fetchData and 'totalGames' in fetchData and 'wins' in fetchData and 'loses' in fetchData and 'kills' in fetchData and 'deaths' in fetchData and 'progress' in fetchData:
            dataDict = {}
            dataDict['flag'] = 13 #Enum Flag.FETCH_ACCOUNT
            dataDict['username'] = fetchData['username']
            dataDict['mmr'] = fetchData['mmr']
            dataDict['totalGames'] = fetchData['totalGames']
            dataDict['wins'] = fetchData['wins']
            dataDict['loses'] = fetchData['loses']
            dataDict['kills'] = fetchData['kills']
            dataDict['deaths'] = fetchData['deaths']
            dataDict['progress'] = fetchData['progress']
            dataMsg = json.dumps(dataDict)

            self.clients_lock.acquire()
            self.moduleSock.sendto(bytes(dataMsg,'utf8'), (self.clients[receiverAddress]['ip'],int(self.clients[receiverAddress]['port'])))
            self.clients_lock.release()
            print('[Notice] Sent profile data of ' + self.clients[targetAddress]['username'] + ' to ' + receiverAddress)
            return True   
      print('[Warning] Receiver client is not logged in; aborting operation...')
      self.sendFlagMsg(self.clients[receiverAddress]['ip'], int(self.clients[receiverAddress]['port']), 16) # Tells client failed to fetch profile data
      return False

   #TODO untested
   def disconnectClient(self, insertAddress):
      self.matchMakingObj.removePlayerFromQueue(insertAddress) #remove player from mm queue if they are there
         
      if insertAddress in self.clients:
         if insertAddress in self.clients[insertAddress]['initialLobby']:
            lobbyKey = self.clients[insertAddress]['initialLobby']

            #If the player is in a lobby: remove player from lobby
            self.matchMakingObj.removePlayerFromLobby(insertAddress, lobbyKey)

            #If player disconencts while in an ongoing match, update everyone on the match of the disconnected player
            if self.matchMakingObj.lobbies[lobbyKey]['inMatch'] == True:
               dropDict = {}
               dropDict['flag'] = 20 
               dropDict['username'] = self.clients[insertAddress]['username']
               dropMsg = json.dumps(dropDict)
               self.sendMsgToLobby(dropMsg, lobbyKey)
         
         #Lastly, remove disconnected player from the connected player list
         self.clients.pop(insertAddress)

   #TODO functionality to be moved to gameplay.py. DEPRECATED
   def updateGameMatch(self, insertLobbyKey):
      if insertLobbyKey in self.matchMakingObj.lobbies:
         if self.matchMakingObj.lobbies[insertLobbyKey]['inMatch'] == True:
            if len(self.matchMakingObj.lobbies[insertLobbyKey]['players']) <= 0:
               print('[Error] Cannot update match; lobby is not in an ongoing match.')
               return

            #Prepare client list
            clientsDict = {}
            clientsDict['flag'] = 19 #Flag.MATCH_UPDATE
            clientsDict['flag']['players'] = []
            
            for clientKey in self.matchMakingObj.lobbies[insertLobbyKey]['players']:
               playerDict = {}
               playerDict['username'] = self.clients[clientKey]['username']
               playerDict['position'] = self.clients[clientKey]['position']
               playerDict['yaw'] = self.clients[clientKey]['yaw']
               playerDict['pitch'] = self.clients[clientKey]['pitch']
               playerDict['latency'] = self.clients[clientKey]['latency']
               playerDict['health'] = self.clients[clientKey]['health']
               clientsDict['flag']['players'].append(playerDict)

            updateMsg = json.dumps(clientsDict)

            #Send out client update list
            self.sendMsgToLobby(updateMsg, insertLobbyKey)

         else:
            print('[Error] Cannot update match; lobby is not in an ongoing match.')
            return
      else:
         print('[Error] Cannot update match; given lobby does not exist.')
         return


def main():
   myServer = Server()
   myServer.launchServer()

if __name__ == '__main__':
   main()
