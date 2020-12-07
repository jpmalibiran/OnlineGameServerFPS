"""
Author: Joseph Malibiran
Last Modified: December 4, 2020
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

   # Sets up server; socket, threads
   def launchServer(self):

      if self.isServerRunning == True:
         print('[Warning] Server already running.')
         return

      self.keepServerRunning = True
      self.isServerRunning = True

      print('[Notice] Launching server: ')
      print('    Setting up socket... ')
      newSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      newSock.bind(('', self.port))

      #start_new_thread(fastRoutines, (s,))
      start_new_thread(self.connectionLoop, (newSock,))
      start_new_thread(self.processMessages, (newSock,))
      start_new_thread(self.slowRoutines, (newSock,))

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
                  self.sendFlagMsg(sock, msgDict['ip'], msgDict['port'], 1) # Tells client it has mutual connection established
               else:
                  self.sendFlagMsg(sock, msgDict['ip'], msgDict['port'], 8) # Tells client it has an invalid version
                  print('[Notice] Client failed to connect due to invalid version. ', msgDict['ip'] + ":"  + msgDict['port'])
            elif msgDict['flag'] == 4: # Client Pong
               if self.verboseDebug:
                  print('[Routine] Received client pong from: ', srcAddress)
               
               if srcAddress in self.clients:
                  self.clients[srcAddress]['lastPong'] = datetime.now()
               else:
                  print('[Error] Client ping has invalid client address key! Aborting proceedure...')
            elif msgDict['flag'] == 16: # Client Login
               if self.checkVersion(msgDict['version']):
                  print('[Notice] Received login attempt from: ', srcAddress)
                  if serverAuth.loginAccount(msgDict['username'], msgDict['password']) == True:
                     self.clients[srcAddress] = {}
                     self.clients[srcAddress]['lastPong'] = datetime.now()
                     self.clients[srcAddress]['username'] = msgDict['username']
                     #self.clients[srcAddress]['id'] = self.getNewClientID()
                     self.clients[srcAddress]['ip'] = str(msgDict['ip'])
                     self.clients[srcAddress]['port'] = str(msgDict['port'])
                     self.clients[srcAddress]['initialLobby'] = 0
                     self.clients[srcAddress]['position'] = {"x": 0,"y": 0,"z": 0}
                     self.clients[srcAddress]['orientation'] = {"yaw": 0,"pitch": 0}
                     self.sendFlagMsg(sock, msgDict['ip'], msgDict['port'], 16) # Tells client it has logged in successfully
                     print('[Notice] Client logged in as ' + msgDict['username'] + '.')
                  else:
                     self.sendFlagMsg(sock, msgDict['ip'], msgDict['port'], 19) # Tells client login has failed
                     print('[Notice] Client  ' + srcAddress + ' failed to log in.')
               else:
                  self.sendFlagMsg(sock, msgDict['ip'], msgDict['port'], 8) # Tells client it has an invalid version
                  print('[Notice] Client failed to connect due to invalid version. ', msgDict['ip'] + ":"  + msgDict['port'])
            elif msgDict['flag'] == 15: # Account registration
               if self.checkVersion(msgDict['version']):
                  print('[Notice] Received registration attempt from: ', srcAddress)
                  if serverAuth.createAccount(msgDict['username'], msgDict['password']) == True:
                     self.sendFlagMsg(sock, msgDict['ip'], msgDict['port'], 15) # Tells client it has registered successfully
                     print('[Notice] Client registered account: ', msgDict['username'])
                  else:
                     self.sendFlagMsg(sock, msgDict['ip'], msgDict['port'], 18) # Tells client registration has failed
                     print('[Notice] Client  ' + srcAddress + ' failed to register account.')
               else:
                  self.sendFlagMsg(sock, msgDict['ip'], msgDict['port'], 8) # Tells client it has an invalid version
                  print('[Notice] Client failed to connect due to invalid version. ', msgDict['ip'] + ":"  + msgDict['port'])
            elif msgDict['flag'] == 9: # Queue Matchmaking
               print('[Notice] Received matchmaking queue request from: ', srcAddress)
               if srcAddress in self.clients:
                  self.matchMakingObj.addPlayerToQueue(srcAddress, 1500)

   #This thread focuses on jobs that will execute every 2 seconds. 
   def slowRoutines(self, sock):
      while True:
         self.routinePing(sock) #Pings every connected client; we expect a Pong message response from each of them. 
         self.routinePongCheck(sock) #If it has been too long since the last Pong response consider that client disconnected and clean up references in the server as well as connected clients

         self.matchMakingObj.sortQueuedPlayers()

         #Subtract 2 seconds from the matchmaking coundown timer every loop. If the countdown reaches 0 create a lobby with the currently queued players.
         if self.matchMakingObj.countdownTimer(-2):
            print('[Notice] Matchmaking Commenced.')
            self.matchMakingObj.startFullLobbies()

         time.sleep(2)

   #Sends a message to client at provided address containing provided flag
   def sendFlagMsg(self, sock, targetIP, targetPort, flagType):
      if self.verboseDebug:
         print('[Routine] Sending flag to client ', targetIP + ":" + targetPort)

      flagDict = {}
      flagDict['flag'] = flagType 
      flagMsg = json.dumps(flagDict)

      self.clients_lock.acquire()
      sock.sendto(bytes(flagMsg,'utf8'), (targetIP, int(targetPort)))
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

         # Every loop, the server checks if a client has not sent a pong in the last 6 seconds.
         if (datetime.now() - self.clients[c]['lastPong']).total_seconds() > self.secondsBeforeClientTimeout:
            droppedClientIP = str(self.clients[c]['ip'])
            droppedClientPort = str(self.clients[c]['port'])
            dropedClientAddress = droppedClientIP + ":" + droppedClientPort
            # Drop the client from the game.
            print('[Notice] Dropped Client: ', droppedClientIP + ":" + droppedClientPort)
            self.clients_lock.acquire()

            #delete player from lobby if applicable TODO untested
            #removePlayerFromLobby(sock, dropedClientAddress)

            del self.clients[dropedClientAddress]
            
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
      else:
         return False

def main():
   myServer = Server()
   myServer.launchServer()

if __name__ == '__main__':
   main()
