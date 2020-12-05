"""
Author: Joseph Malibiran
Last Modified: December 4, 2020
"""

import queue

class Matchmaking:

    def __init__(self):
        self.lobbies = {} 
        self.lobbyQueue = queue.Queue() #Queue of lobbies
        self.playerLobbyQueue = queue.Queue() #Queue of players trying to join a match lobby
        self.initialLobbyKey = 0
        self.lobbyKeyCounter = 0
        self.matchMakingCountdownAmount = 10
        self.matchMakingCountdownTimer = 10

    def countdownTimer(self, additiveAmount):
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

    def addPlayerToQueue(self):
        print('')

    def createNewLobby(self):
        print('')

    