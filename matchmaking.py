"""
Author: Joseph Malibiran
Last Modified: December 2, 2020
"""

import queue

class Matchmaking:

    def __init__(self):
        self.lobbies = {} 
        self.lobbyQueue = queue.Queue() #Queue of lobbies
        self.playerLobbyQueue = queue.Queue() #Queue of players trying to join a match lobby
        self.initialLobbyKey = 0
        self.lobbyKeyCounter = 0

    