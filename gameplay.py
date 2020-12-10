"""
Author: Joseph Malibiran
Last Modified: December 9, 2020
"""

import server as serverScr
import matchmaking as mmScr

class Gameplay:

    def __init__(self, serverRef: serverScr.Server, mmRef: mmScr.Matchmaking):

        #Debug Settings
        self.verboseDebug = False

        self.playersInMatchDict = {}

        self.serverObjRef = serverRef #Server object reference
        self.mmObjRef = mmRef

    def addClientMatchData(self, clientKey: str, lobbyKey: int):
        if clientKey in self.serverObjRef.clients:
            self.playersInMatchDict[clientKey] = {}
            self.playersInMatchDict[clientKey]['username'] = self.serverObjRef.clients[clientKey]['username']
            self.playersInMatchDict[clientKey]['lobbyKey'] = lobbyKey
            self.playersInMatchDict[clientKey]['position'] = {"x": 0,"y": 0,"z": 0}
            self.playersInMatchDict[clientKey]['orientation'] = {"yaw": 0,"pitch": 0}
            self.playersInMatchDict[clientKey]['latency'] = 0
            self.playersInMatchDict[clientKey]['health'] = 100
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

    #From server to each client connected to a match about each client
    def updateMatchData(self):
    
    #From each client to server
    def updateClientHitScan(self):
    
    #From server to each client connected to a match about each client
    def updateMatchHitScans(self):

    def checkGameEnd(self):
    
    #From server to each client connected to a match
    def sendMatchEndData(self):


