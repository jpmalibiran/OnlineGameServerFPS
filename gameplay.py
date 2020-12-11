"""
Author: Joseph Malibiran
Last Modified: December 9, 2020
"""
import time
from datetime import datetime
from _thread import *
import threading
import json

import server as serverScr
import matchmaking as mmScr

class Gameplay:

    def __init__(self, serverRef: serverScr.Server, mmRef: mmScr.Matchmaking):

        #Debug Settings
        self.verboseDebug = False

        self.playersInMatchDict = {}
        self.matchThreads = {}
        

        self.serverObjRef = serverRef #Server object reference
        self.mmObjRef = mmRef

    def newMatchThread(self, lobbyKey: int):
        start_new_thread(self.matchThread, (lobbyKey,))
    
    def matchThread(self, lobbyKey: int):
        self.matchThreads[lobbyKey] = {}
        self.matchThreads[lobbyKey]['persistent'] = True

        while self.matchThreads[lobbyKey]['persistent'] == True:

            self.updateMatchData(lobbyKey)
            time.sleep(0.1) #Repeat 10 times per second

    def addClientMatchData(self, clientKey: str, lobbyKey: int):
        if clientKey in self.serverObjRef.clients:
            self.playersInMatchDict[clientKey] = {}
            self.playersInMatchDict[clientKey]['username'] = self.serverObjRef.clients[clientKey]['username']
            self.playersInMatchDict[clientKey]['address'] = self.serverObjRef.clients[clientKey]['ip'] + ':' + str(self.serverObjRef.clients[clientKey]['port'])
            self.playersInMatchDict[clientKey]['lobbyKey'] = lobbyKey
            self.playersInMatchDict[clientKey]['position'] = {"x": 0,"y": 0,"z": 0}
            self.playersInMatchDict[clientKey]['orientation'] = {"yaw": 0,"pitch": 0}
            self.playersInMatchDict[clientKey]['latency'] = 0
            self.playersInMatchDict[clientKey]['health'] = 100
            self.playersInMatchDict[clientKey]['kills'] = 0
            self.playersInMatchDict[clientKey]['deaths'] = 0
        else:
            print('[Error] Invalid client key or client is not connected to server.')


    def removeClientMatchData(self, clientKey: str):
        if clientKey in self.playersInMatchDict:
            self.playersInMatchDict.pop(clientKey)
        else:
            print('[Error] Invalid client key or client is not in match.')

    def removeAllLobbyMatchData(self, lobbyKey: int):
        if len(self.playersInMatchDict) <= 0:
            return

        for clientKey in self.playersInMatchDict:
            if self.playersInMatchDict[clientKey]['lobbyKey'] == lobbyKey:
                self.playersInMatchDict.pop(clientKey)

    #From each client to server
    def updateClientPositionData(self, clientKey: str, posX: float, posY: float, posZ: float, yaw: float, pitch: float):
        if clientKey in self.playersInMatchDict:
            self.playersInMatchDict[clientKey]['position'] = {posX, posY, posZ}
            self.playersInMatchDict[clientKey]['orientation'] = {yaw, pitch}

    #From server to each client connected to a match 
    def updateMatchData(self, lobbyKey:int):
        if lobbyKey in self.mmObjRef:
            
            if self.mmObjRef.lobbies[lobbyKey]['inMatch'] == False:
                print('[Error] Cannot update match; lobby is not in a match.')
                return

            if len(self.mmObjRef.lobbies[lobbyKey]['players']) <= 0:
                print('[Error] Cannot update match; lobby has no players.')
                return

            #Prepare client list
            clientsDict = {}
            clientsDict['flag'] = 19 #Flag.MATCH_UPDATE
            clientsDict['flag']['players'] = []

            for clientKey in self.mmObjRef.lobbies[lobbyKey]['players']: #TODO untested
                if clientKey in self.playersInMatchDict:
                    playerDict = {}
                    playerDict['username'] = self.playersInMatchDict[clientKey]['username']
                    playerDict['position'] = self.playersInMatchDict[clientKey]['position']
                    playerDict['orientation'] = self.playersInMatchDict[clientKey]['orientation']
                    playerDict['latency'] = self.playersInMatchDict[clientKey]['latency']
                    playerDict['health'] = self.playersInMatchDict[clientKey]['health']
                    clientsDict['flag']['players'].append(playerDict)

            updateMsg = json.dumps(clientsDict)
            self.serverObjRef.sendMsgToLobby(updateMsg, lobbyKey)
        else:
            print('[Error] Cannot update match; lobby does not exist.')

    #From client to server to each client in a match
    def updateHitScan(self, usernameOrigin: str, usernameTarget: str, lobbyKey:int, hitX: float, hitY: float, hitZ: float, damage: int, isHit: bool):
        if usernameOrigin in self.playersInMatchDict:

            if not(usernameTarget in self.playersInMatchDict):
                print('[Error] usernameTarget is not in a match; cannot update gunfire data.')
                return

            #Prepare gunfire network message
            gunFireDict = {}
            gunFireDict['flag'] = 21
            gunFireDict['usernameOrigin'] = usernameOrigin
            gunFireDict['usernameTarget'] = usernameTarget
            gunFireDict['hitPosition'] = {'x': hitX, 'y': hitY, 'z': hitZ}
            gunFireDict['damage'] = damage
            gunFireDict['isHit'] = isHit

            gunFireMsg = json.dumps(gunFireDict)
            self.serverObjRef.sendMsgToLobby(gunFireMsg, lobbyKey)
        else:
            print('[Error] usernameOrigin is not in a match; cannot update gunfire data.')

    #From client to server to each client in a match
    def updateMissShot(self, usernameOrigin: str, lobbyKey:int, hitX: float, hitY: float, hitZ: float):
        if usernameOrigin in self.playersInMatchDict:
            #Prepare gunfire network message
            gunFireDict = {}
            gunFireDict['flag'] = 22
            gunFireDict['usernameOrigin'] = usernameOrigin
            gunFireDict['hitPosition'] = {'x': hitX, 'y': hitY, 'z': hitZ}

            gunFireMsg = json.dumps(gunFireDict)
            self.serverObjRef.sendMsgToLobby(gunFireMsg, lobbyKey)
        else:
            print('[Error] usernameOrigin is not in a match; cannot update gunfire data.')

    def checkGameEnd(self):
        print('')

    #From server to each client connected to a match
    def sendMatchEndData(self):
        print('')


