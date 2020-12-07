"""
Author: Joseph Malibiran
Last Modified: December 4, 2020
"""

import queue

import server as serverScr

class Matchmaking:

    def __init__(self, serverRef: serverScr.Server):
        self.lobbies = {} 
        self.lobbyQueue = queue.Queue() #Queue of lobbies
        #self.playerLobbyQueue = queue.Queue() #Queue of players trying to join a match lobby

        self.playersQueuing = {} #Players queuing for a match

        self.maxLobbySlots = 6
        self.minLobbyPlayers = 3
        self.initialLobbyKey = 0
        self.lobbyKeyCounter = 0
        self.matchMakingCountdownAmount = 10
        self.matchMakingCountdownTimer = 10
        self.amountPlayerPerSort = 36

        self.serverObjRef = serverRef

    def countdownTimer(self, additiveAmount: int):
        if self.matchMakingCountdownTimer > self.matchMakingCountdownAmount or self.matchMakingCountdownTimer <= 0:
            self.matchMakingCountdownTimer = self.matchMakingCountdownAmount
        
        if (self.matchMakingCountdownTimer + additiveAmount) == 0:
            self.matchMakingCountdownTimer = 0
            return True
        elif (self.matchMakingCountdownTimer + additiveAmount) < 0:
            self.matchMakingCountdownTimer = 0
        elif (self.matchMakingCountdownTimer + additiveAmount) > self.matchMakingCountdownAmount:
            self.matchMakingCountdownTimer = self.matchMakingCountdownAmount
        else:
            self.matchMakingCountdownTimer = self.matchMakingCountdownTimer + additiveAmount

        return False

    def addPlayerToQueue(self, address: str, mmr: int):
        self.playersQueuing[address] = mmr

    def removePlayerFromQueue(self, address: str):
        if address in self.playersQueuing:
            self.playersQueuing.pop(address)
            return True

    def removePlayerFromLobby(self, address: str, lobbyKey: int):
        if address in self.lobbies[lobbyKey]['players']:
            self.lobbies[lobbyKey]['players'].remove(address)
            return

        #backup
        for player in self.lobbies[lobbyKey]['players']:
            if player == address:
                self.lobbies[lobbyKey]['players'].remove(address)

    #TODO improve
    def sortQueuedPlayers(self):
        #Skip process if there are no players queuing
        if len(self.playersQueuing) == 0:
            print('[Notice/MMQ] There are no players in matchmaking queue; skipping sort process.')
            return

        print('[Notice/MMQ] Commencing matchmaking queue sort...')

        playerCount = 0
        mmrSum = 0
        mmrAvg = 0
        newLobbyKey = -1
        initialClosestToAvg = 10000
        playerClosestToAvg = self.playersQueuing[0]
        lobbyWithSpaceFound = False

        #Get average MMR
        print('    [Notice/MMQ] Calculating average MMR in queue...')
        for clientKey in self.playersQueuing:
            mmrSum = mmrSum + self.playersQueuing[clientKey]
            playerCount = playerCount + 1
        mmrAvg = mmrSum / playerCount

        print('    [Notice/MMQ] Collecting players with similar MMR in lobbies...')

        loopCounter = 0
        while len(self.playersQueuing) > 0 and loopCounter < self.amountPlayerPerSort:
            loopCounter = loopCounter + 1

            #reset values
            lobbyWithSpaceFound = False
            initialClosestToAvg = 10000

            #Find the player closest to average
            for clientKey in self.playersQueuing:
                if abs(mmrAvg - self.playersQueuing[clientKey]) < abs(mmrAvg - initialClosestToAvg):
                    initialClosestToAvg = self.playersQueuing[clientKey]
                    playerClosestToAvg = clientKey

            #Add player closest to average to lobby
            if len(self.lobbies) < 1: 
                #If no lobby exists yet: make new lobby, add player closest to average to lobby list, remove said player from self.playersQueuing dictionary
                newLobbyKey = self.getNewLobbyIndex()
                self.lobbies[newLobbyKey]['inMatch'] = False
                self.lobbies[newLobbyKey]['players'] = list()
                self.lobbies[newLobbyKey]['players'].append(playerClosestToAvg)
                self.serverObjRef.setPlayerCurrentLobby(playerClosestToAvg, newLobbyKey)
                print('    [Notice/MMQ] Added ' + playerClosestToAvg + ' with MMR:' + self.playersQueuing[playerClosestToAvg] + ' to lobby #' + newLobbyKey)
                self.playersQueuing.pop(playerClosestToAvg)
            else:
                #Find lobby with space, add player closest to average to lobby list, remove said player from self.playersQueuing dictionary
                for lobbyKey in self.lobbies:
                    if len(self.lobbies[lobbyKey]) < self.maxLobbySlots:
                        self.lobbies[lobbyKey]['inMatch'] = False
                        self.lobbies[lobbyKey]['players'] = list()
                        self.lobbies[lobbyKey]['players'].append(playerClosestToAvg)
                        self.serverObjRef.setPlayerCurrentLobby(playerClosestToAvg, lobbyKey)
                        print('    [Notice/MMQ] Added ' + playerClosestToAvg + ' with MMR:' + self.playersQueuing[playerClosestToAvg] + ' to lobby #' + lobbyKey)
                        self.playersQueuing.pop(playerClosestToAvg)
                        lobbyWithSpaceFound = True
                        break
                #If there were no lobbies with empty slots found: create new lobby, add player closest to average, remove said player from self.playersQueuing dictionary
                if lobbyWithSpaceFound == False:
                    newLobbyKey = self.getNewLobbyIndex()
                    self.lobbies[newLobbyKey]['inMatch'] = False
                    self.lobbies[newLobbyKey]['players'] = list()
                    self.lobbies[newLobbyKey]['players'].append(playerClosestToAvg)
                    self.serverObjRef.setPlayerCurrentLobby(playerClosestToAvg, newLobbyKey)
                    print('    [Notice/MMQ] Added ' + playerClosestToAvg + ' with MMR:' + self.playersQueuing[playerClosestToAvg] + ' to lobby #' + newLobbyKey)
                    self.playersQueuing.pop(playerClosestToAvg)

    def startFullLobbies(self):
        if len(self.lobbies) <= 0:
            print('[Notice/MMQ] No lobbies exist; skipping lobby match launches.')
            return

        print('[Notice/MMQ] Commencing available lobby matches.')

        for lobbyKey in self.lobbies:
            #Start match if a lobby has players within self.minLobbyPlayers and self.maxLobbySlots
            if len(self.lobbies[lobbyKey]['players']) >= self.minLobbyPlayers and len(self.lobbies[lobbyKey]['players']) <= self.maxLobbySlots:
                self.lobbies[lobbyKey]['inMatch'] = True
                print('[Notice/MMQ] Match started.')
                self.printLobbyPlayers(lobbyKey)

            #If there are insufficient players, lobby match cannot begin and players will have to wait until next time this function is called.
            #TODO The players will also be removed from the lobby and brought back into queue
            elif len(self.lobbies[lobbyKey]['players']) < self.minLobbyPlayers and len(self.lobbies[lobbyKey]['players']) > 0:
                self.lobbies[lobbyKey]['inMatch'] = False
                print('[Notice/MMQ] Not enough players; ' + str(len(self.lobbies[lobbyKey]['players'])) + ' players on lobby #' + lobbyKey)

            #Error outcomes
            elif len(self.lobbies[lobbyKey]['players']) > self.maxLobbySlots or len(self.lobbies[lobbyKey]['players']) < 0:
                print('[ERROR/MMQ] Invalid player amount (' + str(len(self.lobbies[lobbyKey]['players'])) + ') on lobby #' + lobbyKey)
            else:
                print('[ERROR/MMQ] Unexpected Error; ' + str(len(self.lobbies[lobbyKey]['players'])) + ' players on lobby #' + lobbyKey)

    def printLobbyPlayers(self, lobbyKey):
        lobbyList = ''
        if lobbyKey in self.lobbies:
            lobbyList = lobbyList + '[Notice/MMQ] Lobby #' + lobbyKey
            for playerAddress in self.lobbies[lobbyKey]['players']:
                lobbyList = lobbyList + '\n    - ' + playerAddress
            print(lobbyList)
        else:
            print('[Notice/MMQ] Invalid lobby key; cannot display player list.')

    def getNewLobbyIndex(self):
        self.lobbyKeyCounter = self.lobbyKeyCounter + 1

        if self.lobbyKeyCounter > 65530:
            self.lobbyKeyCounter = 1
        return self.lobbyKeyCounter
    

    