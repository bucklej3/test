#----------------------------#
# Things for just the server #
#----------------------------#
import socket
import select
import sys
import time
#----------------#
import player
import uno
import utilities
#----------------#
from socket import *
from select import *
#----------------#
from player import *
from uno import *
from utilities import *

################################################################################

# Utility Functions #
def displayInfo(HOST, PORT):
    print '##################################################'
    print '# HOST: ' + str(gethostbyname(HOST)) + ' PORT: ' + str(PORT)
    print '# (Input from the keyboard closes the server...) #'
    print '# S->S: Server msg to server                     #'
    print '# S->C: Server msg to client                     #'
    print '# S->A: Server msg to all                        #'
    print '# C->S: Client msg to server                     #'
    print '##################################################\n'
    
def toMsg(head, body):
    msg = '[' + head + '|'
    #Body input is different based on the head
    #Body = string
    if head == 'ACCEPT' or head == 'WAIT' or head == 'INVALID' or head == 'GO' or head == 'UNO' or head == 'GG': 
        msg += body + ']'
        return msg
    if head == 'CHAT':
        msg += body[0] + ',' + body[1] + ']'
        return msg
    #Body = [name, card]
    if head == 'PLAYED':
        msg += body[0] + ',' + body[1] + ']'
        return msg
    #Body = playerList
    if head == 'PLAYERS':
        for p in body:
            if not p.getName() == '':
                if msg == '[' + head + '|':
                    msg += p.getName()
                else:
                    msg += ',' + p.getName()
        return msg + ']'
    #Body = playerList
    if head == 'STARTGAME':
        for p in body:
            if p.isInGame():
                if msg == '[' + head + '|':
                    msg += p.getName()
                else:
                    msg += ',' + p.getName()
        return msg + ']'
    #Body = cards
    if head == 'DEAL':
        for c in body:
            if msg == '[' + head + '|':
                msg += c
            else:
                msg += ',' + c
        return msg + ']'
    #Unknown head
    return msg + 'ERROR]'

def isValidName(name, playerList):
    if len(name) > 8 or name == '' or ',' in name:
        return False
    for p in playerList:
        if p.getName() == name:
            return False
    return True

def send(players, msg, BROADCAST_FLAG):
    if BROADCAST_FLAG == False: #players is just 1 Player class
        print 'S->C: ' + msg
        try:
            players.getClient().sendall(msg)
        except:
            pass
    else: #players is playersList, broadcast to everybody
        print 'S->A: ' + msg
        for p in players:
            try:
                p.getClient().sendall(msg)
            except:
                pass

def handleLobbyMsg(j, playerList, head, body, MAX_PLAYERS):
    if head == 'JOIN':
        if not playerList[j].getName() == '':
            playerList[j].addStrike()
            send(playerList[j], toMsg('INVALID', 'Can only join once'), False)
        ## Assign name from playerNames list ##
        else:
            if not isValidName(body, playerList):
                body = getRandom(playerNames)
            playerList[j].setName(body)
            ## Accept the player ##
            if playersInGame(playerList) < MAX_PLAYERS:
                playerList[j].joinedGame()
                send(playerList[j], toMsg('ACCEPT', playerList[j].getName()), False)
                send(playerList, toMsg('PLAYERS', playerList), True)
            ## Wait the player ##
            else:
                send(playerList[j], toMsg('WAIT', playerList[j].getName()), False)
    elif head == 'CHAT':
        if playerList[j].getName() == '':
            playerList[j].addStrike()
            send(playerList[j], toMsg('INVALID', 'Must join before chat'), False)
        else:
            send(playerList, toMsg('CHAT', [playerList[j].getName(), body]), True)
    else:
        playerList[j].addStrike()
        send(playerList[j], toMsg('INVALID', 'Invalid msg in lobby'), False)

def handleReverse(k, playerList, inputList, msgBuffer):
    p = playerList[k]
    playerList.reverse()
    msgBuffer.reverse()
    serv = inputList.pop(0)
    keyboard = inputList.pop(0)
    inputList.reverse()
    inputList.insert(0, keyboard)
    inputList.insert(0, serv)
    return playerList.index(p)

def handlePlay(body, k, deck, discard, playerList, inputList, msgBuffer, prvNN):
    body = body.upper()
    if not isValidCard(body, discard[0], playerList[k].getHand()):
        playerList[k].addStrike()
        send(playerList[k], toMsg('INVALID', 'Invalid card'), False)
        send(playerList[k], toMsg('GO', getTop(discard)), False)
    else:
        send(playerList, toMsg('PLAYED', [playerList[k].getName(),body]), True)
        if body == 'NN':
            if not prvNN:
                prvNN = True
                tempCards = []
                tempCards.append(dealCard(deck, discard))
                playerList[k].addCards(tempCards)
                send(playerList[k], toMsg('DEAL', tempCards), False)
            else:
                prvNN = False
                k = incr(k, len(playerList))
                while not playerList[k].isInGame():
                    k = incr(k, len(playerList))
                playerList[k].setTime()
            send(playerList[k], toMsg('GO', getTop(discard)), False)
        else:
            prvNN = False
            playerList[k].removeCard(body)
            discard.insert(0, body)
            if len(playerList[k].getHand()) == 1:
                send(playerList, toMsg('UNO', playerList[k].getName()), True)
            #if body[1] == 'U':
                #k = handleReverse(k, playerList, inputList, msgBuffer)
            if len(playerList[k].getHand()) > 0:
                k = incr(k, len(playerList))
                while not playerList[k].isInGame():
                    k = incr(k, len(playerList))
                if body[1] in ['F', 'D']:
                    tempCards = []
                    if body[1] == 'F':
                        y = 4
                    else:
                        y = 2
                    for x in range(0, y):
                        tempCards.append(dealCard(deck, discard))
                    playerList[k].addCards(tempCards)
                    send(playerList[k], toMsg('DEAL', tempCards), False)
                elif body[1] == 'S':
                    k = incr(k, len(playerList))
                    while not playerList[k].isInGame():
                        k = incr(k, len(playerList))
                playerList[k].setTime()
                send(playerList[k], toMsg('GO', getTop(discard)), False)
    return k, prvNN

def handleGameMsg(j, head, body, playerList, inputList, msgBuffer, k, deck, discard, prvNN):
    if head == 'JOIN':
        if not playerList[j].getName() == '':
            playerList[j].addStrike()
            send(playerList[j], toMsg('INVALID', 'Can only join once'), False)
        else:
            if not isValidName(body, playerList):
                body = getRandom(playerNames)
            playerList[j].setName(body)
            send(playerList[j], toMsg('WAIT', playerList[j].getName()), False)
    elif head == 'CHAT':
        if playerList[j].getName() == '':
            playerList[j].addStrike()
            send(playerList[j], toMsg('INVALID', 'Must join before chat'), False)
        else:
            send(playerList, toMsg('CHAT', [playerList[j].getName(), body]), True)
    elif head == 'PLAY':
        if j == k:
            k, prvNN = handlePlay(body, k, deck, discard, playerList, inputList, msgBuffer, prvNN)
        else:
            playerList[j].addStrike()
            send(playerList[j], toMsg('INVALID', 'Can only play on your turn'), False)
    else:
        playerList[j].addStrike()
        send(playerList[j], toMsg('INVALID', 'Invalid msg in game'), False)
    return k, prvNN

def addOneWaiting(playerList):
    for p in playerList:
        if not p.getName() == '' and not p.isInGame():
            p.joinedGame()
            send(p, toMsg('ACCEPT', p.getName()), False)
            break

def addClient(client, address, playerList, inputList, msgBuffer):
    print 'S->S: ' + str(address) + ' has connected.'
    inputList.append(client)
    playerList.append(Player(client))
    msgBuffer.append('')

def disconnect(p, playerList, inputList, msgBuffer):
    name = p.getName()
    i = playerList.index(p)
    print 'S->S: ' + str(p.getClient()) + ' ' + p.getName() + ' has been kicked.'
    p.getClient().close()
    playerList.pop(i)
    msgBuffer.pop(i)
    inputList.pop(i+2)
    if not name == '':
        send(playerList, toMsg('PLAYERS', playerList), True)
        playerNames.append(name)

def disconnectInGame(j, k, discard, playerList, inputList, msgBuffer):
    #j = index of player to disconnect
    #k = index of player whos turn it is
    discard.extend(playerList[j].getHand())
    if j == k:
        kk = incr(k, len(playerList))
        disconnect(playerList[j], playerList, inputList, msgBuffer)
        if kk == 0:
            k = 0
        if playersInGame(playerList) > 0:
            while not playerList[k].isInGame():
                k = incr(k, len(playerList))
            playerList[k].setTime()
            send(playerList[k], toMsg('GO', getTop(discard)), False)
    else:
        disconnect(playerList[j], playerList, inputList, msgBuffer)
        if j < k:
            k -= 1
    return k
            
################################################################################

# Main Lobby Function #
def inLobby(inputList, playerList, msgBuffer, MIN_PLAYERS, MAX_PLAYERS, MAX_MSG, SIZE, MAX_STRIKES, COUNTDOWN_TIME, MAX_LOBBY):
    if len(playerNames) < 100:
        for n in range(0,100):
            if n > 9:
                playerNames.append('Player' + str(n))
            else:
                playerNames.append('Player0' + str(n))
    # Returns false if server keyboard input is detected
    # Returns true if the lobby is transitioning to game
    IN_S_LOBBY = 0          # For parsing client input
    j = 0                   # Index for playerlist and msgBuffer
    msgList = []            # List of msgs
    msgHead = ''            # Head of msg
    msgBody = ''            # Body of msg
    saveMsg = False         # Saves partial msgs for next packet
    isCounting = False      # True when trying to transition to game
    startTime = time.time() # For isCounting transition
    currTime = time.time()  # For isCounting transition
    while True:
        ## Handles Waiting Players ##
        if playersInGame(playerList) < len(playerList):
            if playersInGame(playerList) < MAX_PLAYERS:
                addOneWaiting(playerList)
        ## Handles players over strike limit ##
        for p in playerList:
            if p.getStrikes() >= MAX_STRIKES:
                disconnect(p, playerList, inputList, msgBuffer)
                break
        ## Handles Lobby to Game transition ##
        if not isCounting:
            if playersInGame(playerList) >= MIN_PLAYERS:
                isCounting = True
                startTime = time.time()
        else:
            currTime = time.time()
            if playersInGame(playerList) < MIN_PLAYERS:
                isCounting = False
            elif COUNTDOWN_TIME <= currTime - startTime:
                return True
        ## Handles inputs ##
        inputReady, outputReady, exceptReady = select(inputList, [], [], .1)
        for i in inputReady:
            ## Handles new client connections ##
            if i == inputList[0]:
                client, address = inputList[0].accept()
                if len(playerList) < MAX_LOBBY:
                    addClient(client, address, playerList, inputList, msgBuffer)
                else:
                    client.sendall('[INVALID|Lobby is full, try again later.]')
                    client.close()
            ## Handles server keyboard input ##
            elif i == inputList[1]:
                junk = sys.stdin.readline()
                print 'S->S: Closing server...'
                return False
            ## Handles client data ##
            else:
                j = inputList.index(i) - 2
                try:
                    data = i.recv(SIZE)
                    ## Handles disconnected client ##
                    if not data:
                        disconnect(playerList[j], playerList, inputList, msgBuffer)
                    else:
                        ## Handles unprintable input ##
                        if not isPrintable(data):
                            print 'C->S: ???'
                            playerList[j].addStrike()
                            send(playerList[j], toMsg('INVALID', 'Invalid data input'), False)
                        else:
                            data = removeSpecial(data)
                            print 'C->S: ' + data
                            msgBuffer[j] += data
                            ## Handles large amounts of data ##
                            if len(msgBuffer[j]) > MAX_MSG:
                                playerList[j].addStrike()
                                send(playerList[j], toMsg('INVALID', 'Invalid msg length'), False)
                            else:
                                msgList = parseData(msgBuffer[j], IN_S_LOBBY)
                                ## Handles partial messages ##
                                for m in msgList:
                                    if m.isMsg() == 0:
                                        saveMsg = True
                                if saveMsg:
                                    saveMsg = False
                                else:
                                    for m in msgList:
                                        ## Handles bad messages ##
                                        if m.isMsg() == -1:
                                            playerList[j].addStrike()
                                            send(playerList[j], toMsg('INVALID', m.getBody()), False)
                                        ## Handles good messages ##
                                        elif m.isMsg() == 1:
                                            handleLobbyMsg(j, playerList, m.getHead(), m.getBody(), MAX_PLAYERS)
                                    msgBuffer[j] = ''
                except:
                    disconnect(playerList[j], playerList, inputList, msgBuffer)

################################################################################

# Main Game Function #
def inGame(inputList, playerList, msgBuffer, MIN_PLAYERS, MAX_MSG, SIZE, MAX_STRIKES, TIMEOUT, MAX_LOBBY):
    # Returns false if server keyboard input is detected
    # Returns true if the lobby is transitioning to game
    IN_S_GAME = 1           # For parsing client input
    j = 0                   # Index for playerlist and msgBuffer
    k = 0                   # Index of player whos turn it is
    kk = 0                  # Temp k index when disconnecting the last player in the playerList
    msgList = []            # List of msgs
    msgHead = ''            # Head of msg
    msgBody = ''            # Body of msg
    saveMsg = False         # Saves partial msgs for next packet
    currTime = time.time()  # For timeout of waiting on client input
    deck = []               # Deck for uno (deck[0] is the top)
    discard = []            # Discard for uno (discard[0] is the top)
    prvNN = False           # Previous card played was NN
    ## Set up cards ##
    deck = getNewDeck()
    shuffle(deck)
    discard.append(deck.pop())
    while discard[0] in ['NF', 'NW']:
        deck.append(discard.pop())
        shuffle(deck)
        discard.append(deck.pop())
    send(playerList, toMsg('STARTGAME', playerList), True)
    ## Deal hand to players ##
    for p in playerList:
        if p.isInGame():
            p.setHand(dealHand(deck, discard))
            send(p, toMsg('DEAL', p.getHand()), False)
    ## Tell the first player to start playing ##
    playerList[k].setTime()
    send(playerList[k], toMsg('GO', getTop(discard)), False)
    while True:
        currTime = time.time()
        if not k < len(playerList):
            k = len(playerList)-1
        if not k > 0:
            k = 0
        if len(playerList) > 0:
            ## Handles weird player leavings ##
            if not playerList[k].isInGame():
                if playersInGame(playerList) > 0:
                    while not playerList[k].isInGame():
                        k = incr(k, len(playerList))
                else:
                    return True
            ## Handles player timeout ##
            if currTime - playerList[k].getTime() > TIMEOUT:
                k = disconnectInGame(k, k, discard, playerList, inputList, msgBuffer)
        ## Handles players over strike limit ##
        for q in range(len(playerList)):
            if playerList[q].getStrikes() >= MAX_STRIKES:
                k = disconnectInGame(q, k, discard, playerList, inputList, msgBuffer)
                break
        ## Handles minimum player requirments ##
        try:
            if playersInGame(playerList) < MIN_PLAYERS:
                if MIN_PLAYERS == 2:
                    for q in range(len(playerList)):
                        if playerList[q].isInGame():
                            send(playerList, toMsg('GG',playerList[q].getName()), True)
                            return True
                send(playerList, toMsg('GG','Nobody'), True)
                return True
            ## Handles a player winning ##
            for p in playerList:
                if p.isInGame():
                    if len(p.getHand()) == 0:
                        send(playerList, toMsg('GG', p.getName()), True)
                        return True
        except:
            pass
        ## Handles inputs ##
        inputReady, outputReady, exceptReady = select(inputList, [], [], .1)
        for i in inputReady:
            ## Handles new client connections ##
            if i == inputList[0]:
                client, address = inputList[0].accept()
                if len(playerList) < MAX_LOBBY:
                    addClient(client, address, playerList, inputList, msgBuffer)
                else:
                    client.sendall('[INVALID|Lobby is full, try again later.]')
                    client.close()
            ## Handles server keyboard input ##
            elif i == inputList[1]:
                junk = sys.stdin.readline()
                print 'S->S: Closing server...'
                return False
            ## Handles client data ##
            else:
                j = inputList.index(i) - 2
                try:
                    data = i.recv(SIZE)
                    ## Handles disconnected client ##
                    if not data:
                        k = disconnectInGame(j, k, discard, playerList, inputList, msgBuffer)
                    else:
                        ## Handles unprintable input ##
                        if not isPrintable(data):
                            print 'C->S: ???'
                            playerList[j].addStrike()
                            send(playerList[j], toMsg('INVALID', 'Invalid data input'), False)
                        else:
                            data = removeSpecial(data)
                            print 'C->S: ' + data
                            msgBuffer[j] += data
                            ## Handles large amounts of data ##
                            if len(msgBuffer[j]) > MAX_MSG:
                                playerList[j].addStrike()
                                send(playerList[j], toMsgpoo('INVALID', 'Invalid msg length'), False)
                            else:
                                msgList = parseData(msgBuffer[j], IN_S_GAME)
                                ## Handles partial messages ##
                                for m in msgList:
                                    if m.isMsg() == 0:
                                        saveMsg = True
                                if saveMsg:
                                    saveMsg = False
                                else:
                                    for m in msgList:
                                        ## Handles bad messages ##
                                        if m.isMsg() == -1:
                                            playerList[j].addStrike()
                                            send(playerList[j], toMsg('INVALID', m.getBody()), False)
                                        ## Handles good messages ##
                                        elif m.isMsg() == 1:
                                            k, prvNN = handleGameMsg(j, m.getHead(), m.getBody(), playerList, inputList, msgBuffer, k, deck, discard, prvNN)
                                    msgBuffer[j] = ''
                except:
                    k = disconnectInGame(j, k, discard, playerList, inputList, msgBuffer)
