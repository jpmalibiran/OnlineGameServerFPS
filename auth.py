"""
Author: Dhimant Vyas, Blair White, Joseph Malibiran
Last Modified: December 2, 2020
"""

import requests
import json

#This method creates a new account in the database
def createAccount(username, password):
    print(username + ' is creating a new account...')

    #TODO Create a new profile in the database with the data set: username (string), password (string), id (int), mmr (int). Also include the progression data in whatever form you want.
    # Note: mmr stands for Matchmaking Rating, set the default value to 1000 on new accounts.
    # Note: Ideally, the account database is sorted by id; the partition key should be an int.
    # Return True on successful account creation, return False on failed account creation (username must not be taken, username and password must meet minimum characters required)

    requests.get('https://idoq82v9mh.execute-api.us-east-2.amazonaws.com/default/createAccount', params={'username': username, 'password': password})
    return False

#This method attempts to authenticate with user given login input.
def loginAccount(username, password):
    print(username + ' attempting to log in...')
    #TODO return True on successful login, return False on unsuccessful login
    #requests.get('https://2erht000f7.execute-api.us-east-2.amazonaws.com/default/loginAccount', params={'username': username, 'password': password})
    return True

#This method gets the data about a particular user profile.
def lookupAccount(username):
    profileDict = {}
    print('Fetching account data of account id: ' + str(username))
    #TODO using the given id (int) retrieve the proper player account profile from the database and return it as a dictionary or json.
    requests.get('https://0w1e1jc895.execute-api.us-east-2.amazonaws.com/default/lookupAccount', params={'username': username})
    #Add returned dictionary to profileDict.
    return profileDict
