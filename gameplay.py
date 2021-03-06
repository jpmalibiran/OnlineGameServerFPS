"""
Author: Joseph Malibiran
Last Modified: December 9, 2020
"""
import time
from datetime import datetime
from _thread import *
import threading
import json
import random

#import server as serverScr
#import matchmaking as mmScr

class Gameplay:

    #def __init__(self, serverRef: serverScr.Server, mmRef: mmScr.Matchmaking):
    def __init__(self, serverRef, mmRef):

        #Debug Settings
        self.verboseDebug = False

        self.playersInMatchDict = {}
        self.matchThreads = {}
        

        self.serverObjRef = serverRef #Server object reference
        self.mmObjRef = mmRef

    def newMatchThread(self, lobbyKey: int):
        print('[Notice/Game] Starting new match thread...')
        start_new_thread(self.matchThread, (lobbyKey,))
    
    def matchThread(self, lobbyKey: int):
        self.matchThreads[lobbyKey] = {}
        self.matchThreads[lobbyKey]['persistent'] = True
        self.updateMatchData(lobbyKey)

        while self.matchThreads[lobbyKey]['persistent'] == True:

            self.updateMatchData(lobbyKey)
            time.sleep(0.05) #Repeat 20 times per second

    def addClientMatchData(self, clientKey: str, lobbyKey: int):
        if clientKey in self.serverObjRef.clients:
            self.playersInMatchDict[clientKey] = {}
            self.playersInMatchDict[clientKey]['username'] = self.serverObjRef.clients[clientKey]['username']
            self.playersInMatchDict[clientKey]['address'] = self.serverObjRef.clients[clientKey]['ip'] + ':' + str(self.serverObjRef.clients[clientKey]['port'])
            self.playersInMatchDict[clientKey]['lobbyKey'] = lobbyKey
            self.playersInMatchDict[clientKey]['position'] = {"x": random.randrange(-30,30),"y": 10,"z": random.randrange(-30,30)}
            self.playersInMatchDict[clientKey]['orientation'] = {"yaw": 0,"pitch": 0}
            self.playersInMatchDict[clientKey]['latency'] = 0
            self.playersInMatchDict[clientKey]['health'] = 100
            self.playersInMatchDict[clientKey]['kills'] = 0
            self.playersInMatchDict[clientKey]['deaths'] = 0
        else:
            print('[Error/Game] Invalid client key or client is not connected to server.')

    def removeClientMatchData(self, clientKey: str):
        if clientKey in self.playersInMatchDict:
            self.playersInMatchDict.pop(clientKey)
        else:
            print('[Error/Game] Invalid client key or client is not in match.')

    def removeAllLobbyMatchData(self, lobbyKey: int):
        if len(self.playersInMatchDict) <= 0:
            return

        for clientKey in self.playersInMatchDict:
            if self.playersInMatchDict[clientKey]['lobbyKey'] == lobbyKey:
                self.playersInMatchDict.pop(clientKey)

    #From each client to server
    def updateClientPositionData(self, clientKey: str, posX: float, posY: float, posZ: float, getYaw: float, getPitch: float):
        if clientKey in self.playersInMatchDict:
            self.playersInMatchDict[clientKey]['position'] = {'x': posX, 'y': posY, 'z': posZ}
            self.playersInMatchDict[clientKey]['orientation'] = {'yaw': getYaw, 'pitch': getPitch}

    #From server to each client connected to a match 
    def updateMatchData(self, lobbyKey:int):
        if lobbyKey in self.mmObjRef.lobbies:

            if self.mmObjRef.lobbies[lobbyKey]['inMatch'] == False:
                print('[Error/Game] Cannot update match; lobby is not in a match.')
                return

            if len(self.mmObjRef.lobbies[lobbyKey]['players']) <= 0:
                print('[Error/Game] Cannot update match; lobby has no players.')
                return

            #Prepare client list
            clientsDict = {}
            clientsDict['flag'] = 19 #Flag.MATCH_UPDATE
            clientsDict['players'] = []

            for clientKey in self.mmObjRef.lobbies[lobbyKey]['players']: #TODO untested
                if clientKey in self.playersInMatchDict:
                    playerDict = {}
                    playerDict['username'] = self.playersInMatchDict[clientKey]['username']
                    playerDict['position'] = {}
                    playerDict['position']['x'] = self.playersInMatchDict[clientKey]['position']['x']
                    playerDict['position']['y'] = self.playersInMatchDict[clientKey]['position']['y']
                    playerDict['position']['z'] = self.playersInMatchDict[clientKey]['position']['z']
                    playerDict['orientation'] = {}
                    playerDict['orientation']['yaw'] = self.playersInMatchDict[clientKey]['orientation']['yaw']
                    playerDict['orientation']['pitch'] = self.playersInMatchDict[clientKey]['orientation']['pitch']

                    #playerDict['latency'] = self.playersInMatchDict[clientKey]['latency']
                    playerDict['health'] = self.playersInMatchDict[clientKey]['health']
                    clientsDict['players'].append(playerDict)

                    #if self.verboseDebug:
                        #print('[Temp Debug] self.playersInMatchDict[clientKey]: ' + clientKey)
                        #print('    position: (' + str(self.playersInMatchDict[clientKey]['position']['x']) + ', ' + str(self.playersInMatchDict[clientKey]['position']['y']) + ', ' + str(self.playersInMatchDict[clientKey]['position']['z']) + ') ')
                        #print('    orientation: (' + str(self.playersInMatchDict[clientKey]['orientation']['pitch']) + ', ' + str(self.playersInMatchDict[clientKey]['orientation']['yaw']) + ') ')
                        #print('    health: ' + str(self.playersInMatchDict[clientKey]['health']))
                else:
                    print('[Temp debug] clientKey in self.playersInMatchDict: False')

            try:
                updateMsg = json.dumps(clientsDict)
            except:
                print('[Error/Game] Failed to dump clients dictionary into JSON!')

            #time.sleep(0.001)
            self.serverObjRef.sendMsgToLobby(updateMsg, lobbyKey)
        else:
            print('[Error/Game] Cannot update match; lobby does not exist.')
    
    #From client to server to each client in a match
    def updateHitScan(self, usernameOrigin: str, usernameTarget: str, lobbyKey:int, hitX: float, hitY: float, hitZ: float, damage: int, isHit: bool):
        print('[Notice] Sending hitscan shot update to lobby...')

        #Prepare gunfire network message
        gunFireDict = {}
        gunFireDict['flag'] = 21
        gunFireDict['usernameOrigin'] = usernameOrigin
        gunFireDict['usernameTarget'] = usernameTarget
        gunFireDict['hitPosition'] = {'x': hitX, 'y': hitY, 'z': hitZ}
        gunFireDict['damage'] = damage
        gunFireDict['isHit'] = isHit

        gunFireMsg = json.dumps(gunFireDict)
        #self.serverObjRef.sendMsgToLobby(gunFireMsg, lobbyKey)
        self.serverObjRef.sendMsgToLobbyExclude(gunFireMsg, lobbyKey, usernameOrigin)

    #From client to server to each client in a match
    def updateMissShot(self, usernameOrigin: str, lobbyKey:int, hitX: float, hitY: float, hitZ: float):
        proceed = False

        for clientKey in self.playersInMatchDict:
            if self.playersInMatchDict[clientKey]['username'] == usernameOrigin:
                proceed = True

        if proceed == False:
            print('[Error/Game] usernameOrigin not in self.playersInMatchDict; aborting operation')
            return

        print('[Notice/Game] Sending miss shot update to lobby...')

        #Prepare gunfire network message
        gunFireDict = {}
        gunFireDict['flag'] = 22
        gunFireDict['usernameOrigin'] = usernameOrigin
        gunFireDict['hitPosition'] = {'x': hitX, 'y': hitY, 'z': hitZ}

        gunFireMsg = json.dumps(gunFireDict)
        #self.serverObjRef.sendMsgToLobby(gunFireMsg, lobbyKey)
        self.serverObjRef.sendMsgToLobbyExclude(gunFireMsg, lobbyKey, usernameOrigin)

    def relocatePlayer(self, clientKey):
        if clientKey in self.playersInMatchDict:
            self.playersInMatchDict[clientKey]['position']['x'] = random.randrange(-30,30)
            self.playersInMatchDict[clientKey]['position']['y'] = 10
            self.playersInMatchDict[clientKey]['position']['z'] = random.randrange(-30,30)
        
            respawnDict = {}
            respawnDict['flag'] = 24
            respawnDict['position'] = {}
            respawnDict['position']['x'] = self.playersInMatchDict[clientKey]['position']['x']
            respawnDict['position']['y'] = self.playersInMatchDict[clientKey]['position']['y']
            respawnDict['position']['z'] = self.playersInMatchDict[clientKey]['position']['z']

            respawnMsg = json.dumps(respawnDict)
            self.serverObjRef.sendMsg(clientKey, respawnMsg)
        else:
            print('[Error] Client is not in a match; cannot relocate player.')


    def checkGameEnd(self):
        print('')

    #From server to each client connected to a match
    def sendMatchEndData(self):
        print('')


