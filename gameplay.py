"""
Author: Joseph Malibiran
Last Modified: December 9, 2020
"""
import time
from datetime import datetime
from _thread import *
import threading
import json

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
        start_new_thread(self.matchThread, (lobbyKey,))
    
    def matchThread(self, lobbyKey: int):
        self.matchThreads[lobbyKey] = {}
        self.matchThreads[lobbyKey]['persistent'] = True
        self.updateMatchData(lobbyKey)

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
    def updateClientPositionData(self, clientKey: str, posX: float, posY: float, posZ: float, getYaw: float, getPitch: float):
        if clientKey in self.playersInMatchDict:
            self.playersInMatchDict[clientKey]['position'] = {'x': posX, 'y': posY, 'z': posZ}
            self.playersInMatchDict[clientKey]['orientation'] = {'yaw': getYaw, 'pitch': getPitch}
            if self.verboseDebug == True:
                print('[Temp debug] updateClientPositionData(): ')
                print('[Temp debug] client: ' + str(self.playersInMatchDict[clientKey]['username']))
                print('[Temp debug] position: (' + str(posX) + ', ' + str(posY) + ', ' + str(posZ) +')')
                print('[Temp debug] yaw: ' + str(yaw))
                print('[Temp debug] pitch: ' + str(pitch))

    #From server to each client connected to a match 
    def updateMatchData(self, lobbyKey:int):
        print('[Temp debug] updateMatchData A: ')
        if lobbyKey in self.mmObjRef.lobbies:
            
            print('[Temp debug] updateMatchData B: ')

            if self.mmObjRef.lobbies[lobbyKey]['inMatch'] == False:
                print('[Error] Cannot update match; lobby is not in a match.')
                return

            if len(self.mmObjRef.lobbies[lobbyKey]['players']) <= 0:
                print('[Error] Cannot update match; lobby has no players.')
                return

            print('[Temp debug] updateMatchData C: ')

            #Prepare client list
            clientsDict = {}
            clientsDict['flag'] = 19 #Flag.MATCH_UPDATE
            clientsDict['players'] = []

            for clientKey in self.mmObjRef.lobbies[lobbyKey]['players']: #TODO untested
                print('[Temp debug] for clientKey in self.mmObjRef.lobbies[lobbyKey][players]: ')
                if clientKey in self.playersInMatchDict:
                    print('[Temp debug] clientKey in self.playersInMatchDict: True')
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
                else:
                    print('[Temp debug] clientKey in self.playersInMatchDict: False')

            print('[Temp debug] updateMatchData self.playersInMatchDict[clientKey] D: ')
            print('[Temp debug] client: ' + str(self.playersInMatchDict[clientKey]['username']))
            print('[Temp debug] position: (' + str(self.playersInMatchDict[clientKey]['position']['x']) + ', ' + str(self.playersInMatchDict[clientKey]['position']['y']) + ', ' + str(self.playersInMatchDict[clientKey]['position']['z']) +')')
            print('[Temp debug] yaw: ' + str(self.playersInMatchDict[clientKey]['orientation']['yaw']))
            print('[Temp debug] pitch: ' + str(self.playersInMatchDict[clientKey]['orientation']['pitch']))

            print('[Temp debug] updateMatchData playerDict E: ')
            print('[Temp debug] client: ' + str(playerDict['username']))
            print('[Temp debug] position: (' + str(playerDict['position']['x']) + ', ' + str(playerDict['position']['y']) + ', ' + str(playerDict['position']['z']) +')')
            print('[Temp debug] yaw: ' + str(playerDict['orientation']['yaw']))
            print('[Temp debug] pitch: ' + str(playerDict['orientation']['pitch']))

            try:
                updateMsg = json.dumps(clientsDict)
            except:
                print('[Error] Failed to dump clients dictionary into JSON!')

            print('[Temp debug] updateMatchData F: ')
            #time.sleep(0.001)
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


