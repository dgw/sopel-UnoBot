"""
Copyright 2010 Tamas Marki. All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are
permitted provided that the following conditions are met:

   1. Redistributions of source code must retain the above copyright notice, this list of
      conditions and the following disclaimer.

   2. Redistributions in binary form must reproduce the above copyright notice, this list
      of conditions and the following disclaimer in the documentation and/or other materials
      provided with the distribution.

THIS SOFTWARE IS PROVIDED BY TAMAS MARKI ``AS IS'' AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL TAMAS MARKI OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


[18:03] <Lako> .play w 3
[18:03] <unobot> TopMobil's turn. Top Card: *]
[18:03] [Notice] -unobot- Your cards: [4][9][4][8][D2][D2]
[18:03] [Notice] -unobot- Next: hatcher (5 cards) - Lako (2 cards)
[18:03] <TopMobil> :O
[18:03] <Lako> :O

"""

import willie.module as module
import random
from datetime import datetime, timedelta

CHANNEL = '#Kaede'
SCOREFILE = "/var/lib/willie/unoscores.txt"

STRINGS = {
    'ALREADY_STARTED' : 'Game already started by %s! Type join to join!',
    'GAME_STARTED'    : 'IRC-UNO started by %s - Type join to join!',
    'GAME_STOPPED'    : 'Game stopped.',
    'CANT_STOP'       : '%s is the game owner, you can\'t stop it!',
    'DEALING_IN'      : 'Dealing %s into the game as player #%s!',
    'JOINED'          : 'Dealing %s into the game as player #%s!',
    'ENOUGH'          : 'There are enough players to deal now.',
    'NOT_STARTED'     : 'Game not started.',
    'NOT_ENOUGH'      : 'Not enough players to deal yet.',
    'NEEDS_TO_DEAL'   : '%s needs to deal.',
    'ALREADY_DEALT'   : 'Already dealt.',
    'ON_TURN'         : 'It\'s %s\'s turn.',
    'DONT_HAVE'       : 'You don\'t have that card, %s',
    'DOESNT_PLAY'     : 'That card does not play, %s',
    'UNO'             : 'UNO! %s has ONE card left!',
    'WIN'             : 'We have a winner: %s!!! This game took %s',
    'DRAWN_ALREADY'   : 'You\'ve already drawn, either play or pass.',
    'DRAWS'           : '%s draws a card',
    'DRAWN_CARD'      : 'Drawn card: %s',
    'DRAW_FIRST'      : '%s, you need to draw first!',
    'PASSED'          : '%s passed!',
    'NO_SCORES'       : 'No scores yet',
    'SCORE_ROW'       : '#%s %s (%s points %s games, %s won, %s wasted)',
    'TOP_CARD'        : '%s\'s turn. Top Card: %s',
    'YOUR_CARDS'      : 'Your cards: %s',
    'NEXT_START'      : 'Next: ',
    'NEXT_PLAYER'     : '%s (%s cards)',
    'D2'              : '%s draws two and is skipped!',
    'CARDS'           : 'Cards: %s',
    'WD4'             : '%s draws four and is skipped!',
    'SKIPPED'         : '%s is skipped!',
    'REVERSED'        : 'Order reversed!',
    'GAINS'           : '%s gains %s points!',
}  # yapf: disable


class UnoBot:
    def __init__(self):
        self.colored_card_nums = ['1', '2', '3', '4', '5', '6', '7', '8', '9',
                                  'R', 'S', 'D2']
        self.special_scores = {'R': 20, 'S': 20, 'D2': 20, 'WD4': 50, 'W': 50}
        self.colors = 'RGBY'
        self.special_cards = ['W', 'WD4']
        self.players = {}
        self.playerOrder = []
        self.game_on = False
        self.currentPlayer = 0
        self.topCard = None
        self.way = 1
        self.drawn = False
        self.scoreFile = SCOREFILE
        self.deck = []

    def start(self, bot, owner):
        if self.game_on:
            bot.msg(CHANNEL, STRINGS['ALREADY_STARTED'] % self.game_on)
        else:
            self.game_on = owner
            self.deck = []
            bot.msg(CHANNEL, STRINGS['GAME_STARTED'] % owner)
            self.players = {}
            self.players[owner] = []
            self.playerOrder = [owner]

    def stop(self, bot, trigger):
        if trigger.nick == self.game_on:
            bot.msg(CHANNEL, STRINGS['GAME_STOPPED'])
            self.game_on = False
        elif self.game_on:
            bot.msg(CHANNEL, STRINGS['CANT_STOP'] % self.game_on)

    def join(self, bot, trigger):
        #print dir (bot.bot)
        #print dir (trigger)
        if self.game_on:
            if trigger.nick not in self.players:
                self.players[trigger.nick] = []
                self.playerOrder.append(trigger.nick)
                if self.deck:
                    for i in xrange(0, 7):
                        self.players[trigger.nick].append(self.getCard())
                    bot.msg(CHANNEL, STRINGS['DEALING_IN'] % (
                        trigger.nick, self.playerOrder.index(trigger.nick) + 1
                    ))
                else:
                    bot.msg(CHANNEL, STRINGS['JOINED'] % (
                        trigger.nick, self.playerOrder.index(trigger.nick) + 1
                    ))
                    if len(self.players) > 1:
                        bot.msg(CHANNEL, STRINGS['ENOUGH'])
        else:
            bot.msg(CHANNEL, STRINGS['NOT_STARTED'])

    def deal(self, bot, trigger):
        if not self.game_on:
            bot.msg(CHANNEL, STRINGS['NOT_STARTED'])
            return
        if len(self.players) < 2:
            bot.msg(CHANNEL, STRINGS['NOT_ENOUGH'])
            return
        if trigger.nick != self.game_on:
            bot.msg(CHANNEL, STRINGS['NEEDS_TO_DEAL'] % self.game_on)
            return
        if len(self.deck):
            bot.msg(CHANNEL, STRINGS['ALREADY_DEALT'])
            return
        self.startTime = datetime.now()
        self.deck = self.createnewdeck()
        for i in xrange(0, 7):
            for p in self.players:
                self.players[p].append(self.getCard())
        self.topCard = self.getCard()
        while self.topCard in ['W', 'WD4']:
            self.topCard = self.getCard()
        self.currentPlayer = 1
        self.cardPlayed(bot, self.topCard)
        self.showOnTurn(bot)

    def play(self, bot, trigger):
        if not self.game_on or not self.deck:
            return
        if trigger.nick != self.playerOrder[self.currentPlayer]:
            bot.msg(CHANNEL,
                    STRINGS['ON_TURN'] % self.playerOrder[self.currentPlayer])
            return
        tok = [z.strip() for z in str(trigger).upper().split(' ')]
        if len(tok) != 3:
            return
        searchcard = ''
        if tok[1] in self.special_cards:
            searchcard = tok[1]
        else:
            searchcard = (tok[1] + tok[2])
        if searchcard not in self.players[self.playerOrder[self.currentPlayer]
                                          ]:
            bot.msg(CHANNEL, STRINGS['DONT_HAVE'] %
                    self.playerOrder[self.currentPlayer])
            return
        playcard = (tok[1] + tok[2])
        if not self.cardPlayable(playcard):
            bot.msg(CHANNEL, STRINGS['DOESNT_PLAY'] %
                    self.playerOrder[self.currentPlayer])
            return

        self.drawn = False
        self.players[self.playerOrder[self.currentPlayer]].remove(searchcard)

        pl = self.currentPlayer

        self.incPlayer()
        self.cardPlayed(bot, playcard)

        if len(self.players[self.playerOrder[pl]]) == 1:
            bot.msg(CHANNEL, STRINGS['UNO'] % self.playerOrder[pl])
        elif len(self.players[self.playerOrder[pl]]) == 0:
            bot.msg(CHANNEL,
                    STRINGS['WIN'] % (self.playerOrder[pl],
                                      (datetime.now() - self.startTime)))
            self.gameEnded(bot, self.playerOrder[pl])
            return

        self.showOnTurn(bot)

    def draw(self, bot, trigger):
        if not self.game_on or not self.deck:
            return
        if trigger.nick != self.playerOrder[self.currentPlayer]:
            bot.msg(CHANNEL,
                    STRINGS['ON_TURN'] % self.playerOrder[self.currentPlayer])
            return
        if self.drawn:
            bot.msg(CHANNEL, STRINGS['DRAWN_ALREADY'])
            return
        self.drawn = True
        bot.msg(CHANNEL,
                STRINGS['DRAWS'] % self.playerOrder[self.currentPlayer])
        c = self.getCard()
        self.players[self.playerOrder[self.currentPlayer]].append(c)
        bot.notice(STRINGS['DRAWN_CARD'] % self.renderCards([c]), trigger.nick)

    # this is not a typo, avoiding collision with Python's pass keyword
    def passs(self, bot, trigger):
        if not self.game_on or not self.deck:
            return
        if trigger.nick != self.playerOrder[self.currentPlayer]:
            bot.msg(CHANNEL,
                    STRINGS['ON_TURN'] % self.playerOrder[self.currentPlayer])
            return
        if not self.drawn:
            bot.msg(CHANNEL, STRINGS['DRAW_FIRST'] %
                    self.playerOrder[self.currentPlayer])
            return
        self.drawn = False
        bot.msg(CHANNEL,
                STRINGS['PASSED'] % self.playerOrder[self.currentPlayer])
        self.incPlayer()
        self.showOnTurn(bot)

    def top10(self, bot):
        from copy import copy
        prescores = []
        try:
            f = open(self.scoreFile, 'r')
            for l in f:
                t = l.replace('\n', '').split(' ')
                if len(t) < 4: continue
                prescores.append(copy(t))
                if len(t) == 4: t.append(0)
            f.close()
        except:
            pass
        prescores = sorted(prescores, lambda x, y: cmp(
            (y[1] != '0') and (float(y[3]) / int(y[1])) or 0, (x[1] != '0') and
            (float(x[3]) / int(x[1])) or 0))
        if not prescores:
            bot.msg(CHANNEL, STRINGS['NO_SCORES'])
        i = 1
        for z in prescores[:10]:
            bot.msg(CHANNEL, STRINGS['SCORE_ROW'] %
                    (i, z[0], z[3], z[1], z[2], timedelta(seconds=int(z[4]))))
            i += 1

    def createnewdeck(self):
        ret = []
        for a in self.colored_card_nums:
            for b in self.colors:
                ret.append(b + a)
        for a in self.special_cards:
            ret.append(a)
            ret.append(a)

        ret *= 2
        random.shuffle(ret)
        return ret

    def getCard(self):
        ret = self.deck[0]
        self.deck.pop(0)
        if not self.deck:
            self.deck = self.createnewdeck()
        return ret

    def showOnTurn(self, bot):
        bot.msg(CHANNEL,
                STRINGS['TOP_CARD'] % (self.playerOrder[self.currentPlayer],
                                       self.renderCards([self.topCard])))
        bot.notice(STRINGS['YOUR_CARDS'] % self.renderCards(
            self.players[self.playerOrder[self.currentPlayer]]),
                   self.playerOrder[self.currentPlayer])
        msg = STRINGS['NEXT_START']
        tmp = self.currentPlayer + self.way
        if tmp == len(self.players):
            tmp = 0
        if tmp < 0:
            tmp = len(self.players) - 1
        arr = []
        while tmp != self.currentPlayer:
            arr.append(STRINGS['NEXT_PLAYER'] % (self.playerOrder[tmp], len(
                self.players[self.playerOrder[tmp]])))
            tmp = tmp + self.way
            if tmp == len(self.players):
                tmp = 0
            if tmp < 0:
                tmp = len(self.players) - 1
        msg += ' - '.join(arr)
        bot.notice(msg, self.playerOrder[self.currentPlayer])

    def renderCards(self, cards):
        ret = []
        for c in sorted(cards):
            if c in ['W', 'WD4']:
                ret.append('\x0301[' + c + ']')
                continue
            if c[0] == 'W':
                c = c[-1] + '*'
            t = '\x0300\x03'
            if c[0] == 'B':
                t += '12['
            if c[0] == 'Y':
                t += '08['
            if c[0] == 'G':
                t += '09['
            if c[0] == 'R':
                t += '04['
            t += c[1:] + ']\x03'
            ret.append(t)
        return ''.join(ret)

    def cardPlayable(self, card):
        if card[0] == 'W' and card[-1] in self.colors:
            return True
        if self.topCard[0] == 'W':
            return card[0] == self.topCard[-1]
        return ((card[0] == self.topCard[0]) or
                (card[1] == self.topCard[1])) and (card[0] not in ['W', 'WD4'])

    def cardPlayed(self, bot, card):
        if card[1:] == 'D2':
            bot.msg(CHANNEL,
                    STRINGS['D2'] % self.playerOrder[self.currentPlayer])
            z = [self.getCard(), self.getCard()]
            bot.notice(STRINGS['CARDS'] % self.renderCards(z),
                       self.playerOrder[self.currentPlayer])
            self.players[self.playerOrder[self.currentPlayer]].extend(z)
            self.incPlayer()
        elif card[:2] == 'WD':
            bot.msg(CHANNEL,
                    STRINGS['WD4'] % self.playerOrder[self.currentPlayer])
            z = [self.getCard(), self.getCard(), self.getCard(),
                 self.getCard()]
            bot.notice(STRINGS['CARDS'] % self.renderCards(z),
                       self.playerOrder[self.currentPlayer])
            self.players[self.playerOrder[self.currentPlayer]].extend(z)
            self.incPlayer()
        elif card[1] == 'S':
            bot.msg(CHANNEL,
                    STRINGS['SKIPPED'] % self.playerOrder[self.currentPlayer])
            self.incPlayer()
        elif card[1] == 'R' and card[0] != 'W':
            bot.msg(CHANNEL, STRINGS['REVERSED'])
            self.way = -self.way
            self.incPlayer()
            self.incPlayer()
        self.topCard = card

    def gameEnded(self, bot, winner):
        try:
            score = 0
            for p in self.players:
                for c in self.players[p]:
                    if c[0] == 'W':
                        score += self.special_scores[c]
                    elif c[1] in ['S', 'R', 'D']:
                        score += self.special_scores[c[1:]]
                    else:
                        score += int(c[1])
            bot.msg(CHANNEL, STRINGS['GAINS'] % (winner, score))
            self.saveScores(self.players.keys(), winner, score,
                            (datetime.now() - self.startTime).seconds)
        except Exception, e:
            print 'Score error: %s' % e
        self.players = {}
        self.playerOrder = []
        self.game_on = False
        self.currentPlayer = 0
        self.topCard = None
        self.way = 1

    def incPlayer(self):
        self.currentPlayer = self.currentPlayer + self.way
        if self.currentPlayer == len(self.players):
            self.currentPlayer = 0
        if self.currentPlayer < 0:
            self.currentPlayer = len(self.players) - 1

    def saveScores(self, players, winner, score, time):
        from copy import copy
        prescores = {}
        try:
            f = open(self.scoreFile, 'r')
            for l in f:
                t = l.replace('\n', '').split(' ')
                if len(t) < 4: continue
                if len(t) == 4: t.append(0)
                prescores[t[0]] = [t[0], int(t[1]), int(t[2]), int(t[3]),
                                   int(t[4])]
            f.close()
        except:
            pass
        for p in players:
            if p not in prescores:
                prescores[p] = [p, 0, 0, 0, 0]
            prescores[p][1] += 1
            prescores[p][4] += time
        prescores[winner][2] += 1
        prescores[winner][3] += score
        try:
            f = open(self.scoreFile, 'w')
            for p in prescores:
                f.write(' '.join([str(s) for s in prescores[p]]) + '\n')
            f.close()
        except Exception, e:
            print 'Failed to write score file %s' % e


unobot = UnoBot()


@module.commands('uno')
@module.example('.uno')
@module.priority('high')
def uno(bot, trigger):
    unobot.start(bot, trigger.nick)


@module.commands('unostop')
@module.example('.unostop')
@module.priority('high')
def unostop(bot, trigger):
    unobot.stop(bot, trigger)


@module.rule('^join$')
@module.priority('high')
def join(bot, trigger):
    unobot.join(bot, trigger)


@module.commands('deal')
@module.priority('high')
def deal(bot, trigger):
    unobot.deal(bot, trigger)


@module.commands('play')
@module.priority('high')
def play(bot, trigger):
    unobot.play(bot, trigger)


@module.commands('draw')
@module.priority('high')
def draw(bot, trigger):
    unobot.draw(bot, trigger)


@module.commands('pass')
@module.priority('high')
def passs(bot, trigger):
    unobot.passs(bot, trigger)


@module.commands('unotop10')
@module.priority('high')
def unotop10(bot, trigger):
    unobot.top10(bot)


if __name__ == '__main__':
    print __doc__.strip()
