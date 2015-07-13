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
import willie.tools as tools
import json, random
from datetime import datetime, timedelta

SCOREFILE = "/var/lib/willie/unoscores.txt"

YES = True
NO = False
STRINGS = {
    'ALREADY_STARTED': 'Game already started by %s! Type join to join!',
    'GAME_STARTED'   : 'IRC-UNO started by %s - Type join to join!',
    'GAME_STOPPED'   : 'Game stopped.',
    'CANT_STOP'      : '%s is the game owner, you can\'t stop it!',
    'DEALING_IN'     : 'Dealing %s into the game as player #%s!',
    'JOINED'         : 'Dealing %s into the game as player #%s!',
    'ENOUGH'         : 'There are enough players to deal now.',
    'NOT_STARTED'    : 'Game not started.',
    'NOT_ENOUGH'     : 'Not enough players to deal yet.',
    'NEEDS_TO_DEAL'  : '%s needs to deal.',
    'ALREADY_DEALT'  : 'Already dealt.',
    'ON_TURN'        : 'It\'s %s\'s turn.',
    'DONT_HAVE'      : 'You don\'t have that card!',
    'DOESNT_PLAY'    : 'That card can\'t be played now.',
    'UNO'            : 'UNO! %s has ONE card left!',
    'WIN'            : 'We have a winner: %s!!! This game took %s',
    'DRAWN_ALREADY'  : 'You\'ve already drawn, either play or pass.',
    'DRAWN_CARD'     : 'You drew: %s',
    'DRAW_FIRST'     : 'You have to draw first.',
    'PASSED'         : '%s passed!',
    'NO_SCORES'      : 'No scores yet',
    'SCORE_ROW'      : '#%s %s (%s points %s games, %s won, %s wasted)',
    'TOP_CARD'       : '%s\'s turn. Top Card: %s',
    'YOUR_CARDS'     : 'Your cards (%d): %s',
    'NEXT_START'     : 'Next: ',
    'SB_START'       : 'Standings: ',
    'SB_PLAYER'      : '%s (%s cards)',
    'D2'             : '%s draws two and is skipped!',
    'CARDS'          : 'Cards: %s',
    'WD4'            : '%s draws four and is skipped!',
    'SKIPPED'        : '%s is skipped!',
    'REVERSED'       : 'Order reversed!',
    'GAINS'          : '%s gains %s points!',
}  # yapf: disable
COLORED_CARD_NUMS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'R', 'S', 'D2']
CARD_COLORS = 'RGBY'
SPECIAL_CARDS = ['W', 'WD4']


class UnoGame:
    def __init__(self, bot, trigger):
        self.owner = trigger.nick
        self.channel = trigger.sender
        self.deck = []
        self.players = {self.owner: []}
        self.playerOrder = [self.owner]
        self.currentPlayer = 0
        self.topCard = None
        self.way = 1
        self.drawn = NO
        self.deck = []
        self.startTime = None

    def join(self, bot, trigger):
        if trigger.nick not in self.players:
            self.players[trigger.nick] = []
            self.playerOrder.append(trigger.nick)
            if self.deck:
                for i in xrange(0, 7):
                    self.players[trigger.nick].append(self.getCard())
                bot.say(STRINGS['DEALING_IN'] % (
                    trigger.nick, self.playerOrder.index(trigger.nick) + 1
                ))
            else:
                bot.say(STRINGS['JOINED'] % (
                    trigger.nick, self.playerOrder.index(trigger.nick) + 1
                ))
                if len(self.players) > 1:
                    bot.notice(STRINGS['ENOUGH'], self.owner)

    def deal(self, bot, trigger):
        if len(self.players) < 2:
            bot.say(STRINGS['NOT_ENOUGH'])
            return
        if trigger.nick != self.owner and not trigger.admin:
            bot.say(STRINGS['NEEDS_TO_DEAL'] % self.owner)
            return
        if len(self.deck):
            bot.say(STRINGS['ALREADY_DEALT'])
            return
        self.startTime = datetime.now()
        self.deck = self.createDeck()
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
        if not self.deck:
            return
        if trigger.nick != self.playerOrder[self.currentPlayer]:
            bot.say(STRINGS['ON_TURN'] % self.playerOrder[self.currentPlayer])
            return
        tok = [z.strip() for z in str(trigger).upper().split(' ')]
        if len(tok) != 3:
            return
        if tok[1] in SPECIAL_CARDS:
            searchcard = tok[1]
        else:
            searchcard = (tok[1] + tok[2])
        if searchcard not in self.players[self.playerOrder[self.currentPlayer]]:
            bot.notice(STRINGS['DONT_HAVE'], self.playerOrder[self.currentPlayer])
            return
        playcard = (tok[1] + tok[2])
        if not self.cardPlayable(playcard):
            bot.notice(STRINGS['DOESNT_PLAY'],
                       self.playerOrder[self.currentPlayer])
            return
        self.drawn = NO
        self.players[self.playerOrder[self.currentPlayer]].remove(searchcard)

        pl = self.currentPlayer

        self.incPlayer()
        self.cardPlayed(bot, playcard)

        if len(self.players[self.playerOrder[pl]]) == 1:
            bot.say(STRINGS['UNO'] % self.playerOrder[pl])
        elif len(self.players[self.playerOrder[pl]]) == 0:
            return 'WIN'

        self.showOnTurn(bot)

    def draw(self, bot, trigger):
        if not self.deck:
            return
        if trigger.nick != self.playerOrder[self.currentPlayer]:
            bot.say(STRINGS['ON_TURN'] % self.playerOrder[self.currentPlayer])
            return
        if self.drawn:
            bot.notice(STRINGS['DRAWN_ALREADY'],
                       self.playerOrder[self.currentPlayer])
            return
        self.drawn = YES
        c = self.getCard()
        self.players[self.playerOrder[self.currentPlayer]].append(c)
        bot.notice(STRINGS['DRAWN_CARD'] % self.renderCards([c]), trigger.nick)

    # this is not a typo, avoiding collision with Python's pass keyword
    def passs(self, bot, trigger):
        if not self.deck:
            return
        if trigger.nick != self.playerOrder[self.currentPlayer]:
            bot.say(STRINGS['ON_TURN'] % self.playerOrder[self.currentPlayer])
            return
        if not self.drawn:
            bot.notice(STRINGS['DRAW_FIRST'],
                       self.playerOrder[self.currentPlayer])
            return
        self.drawn = NO
        bot.say(STRINGS['PASSED'] % self.playerOrder[self.currentPlayer])
        self.incPlayer()
        self.showOnTurn(bot)

    def showOnTurn(self, bot):
        pl = self.playerOrder[self.currentPlayer]
        bot.say(STRINGS['TOP_CARD'] % (pl, self.renderCards([self.topCard])))
        self.sendCards(bot, self.playerOrder[self.currentPlayer])
        self.sendNext(bot)

    def sendCards(self, bot, who):
        cards = self.players[who]
        bot.notice(STRINGS['YOUR_CARDS'] % (len(cards), self.renderCards(cards)), who)

    def sendNext(self, bot):
        bot.notice(STRINGS['NEXT_START'] + self.renderCounts(), self.playerOrder[self.currentPlayer])

    def sendCounts(self, bot):
        bot.say(STRINGS['SB_START'] + self.renderCounts(YES))

    def renderCounts(self, full=NO):
        if full:
            stop = len(self.players)
            inc = abs(self.way)
            plr = 0
        else:
            stop = self.currentPlayer
            inc = self.way
            plr = stop + inc
            if plr == len(self.players):
                plr = 0
            if plr < 0:
                plr = len(self.players) - 1
        arr = []
        while plr != stop:
            arr.append(STRINGS['SB_PLAYER'] % (self.playerOrder[plr], len(
                self.players[self.playerOrder[plr]])))
            plr += inc
            if plr == len(self.players) and not full:
                plr = 0
            if plr < 0:
                plr = len(self.players) - 1
        return ' - '.join(arr)

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
        if card[0] == 'W' and card[-1] in CARD_COLORS:
            return True
        if self.topCard[0] == 'W':
            return card[0] == self.topCard[-1]
        return ((card[0] == self.topCard[0]) or
                (card[1] == self.topCard[1])) and (card[0] not in ['W', 'WD4'])

    def cardPlayed(self, bot, card):
        if card[1:] == 'D2':
            bot.say(STRINGS['D2'] % self.playerOrder[self.currentPlayer])
            z = [self.getCard(), self.getCard()]
            bot.notice(STRINGS['CARDS'] % self.renderCards(z),
                       self.playerOrder[self.currentPlayer])
            self.players[self.playerOrder[self.currentPlayer]].extend(z)
            self.incPlayer()
        elif card[:2] == 'WD':
            bot.say(STRINGS['WD4'] % self.playerOrder[self.currentPlayer])
            z = [self.getCard(), self.getCard(), self.getCard(),
                 self.getCard()]
            bot.notice(STRINGS['CARDS'] % self.renderCards(z),
                       self.playerOrder[self.currentPlayer])
            self.players[self.playerOrder[self.currentPlayer]].extend(z)
            self.incPlayer()
        elif card[1] == 'S':
            bot.say(STRINGS['SKIPPED'] % self.playerOrder[self.currentPlayer])
            self.incPlayer()
        elif card[1] == 'R' and card[0] != 'W':
            bot.say(STRINGS['REVERSED'])
            self.way = -self.way
            self.incPlayer()
            self.incPlayer()
        self.topCard = card

    def getCard(self):
        ret = self.deck[0]
        self.deck.pop(0)
        if not self.deck:
            self.deck = self.createDeck()
        return ret

    def createDeck(self):
        ret = []
        for a in COLORED_CARD_NUMS:
            for b in CARD_COLORS:
                ret.append(b + a)
        for a in SPECIAL_CARDS:
            ret.append(a)
            ret.append(a)

        ret *= 2
        random.shuffle(ret)
        return ret

    def incPlayer(self):
        self.currentPlayer += self.way
        if self.currentPlayer == len(self.players):
            self.currentPlayer = 0
        if self.currentPlayer < 0:
            self.currentPlayer = len(self.players) - 1


class UnoBot:
    def __init__(self):
        self.special_scores = {'R': 20, 'S': 20, 'D2': 20, 'WD4': 50, 'W': 50}
        self.scoreFile = SCOREFILE
        self.games = {}

    def start(self, bot, trigger):
        if trigger.sender in self.games:
            bot.say(STRINGS['ALREADY_STARTED'] % self.games[trigger.sender].owner)
        else:
            self.games[trigger.sender] = UnoGame(bot, trigger)
            bot.say(STRINGS['GAME_STARTED'] % self.games[trigger.sender].owner)

    def stop(self, bot, trigger):
        if trigger.sender in self.games:
            game = self.games[trigger.sender]
            if trigger.nick == game.owner or trigger.admin:
                bot.say(STRINGS['GAME_STOPPED'])
                del self.games[trigger.sender]
            else:
                bot.say(STRINGS['CANT_STOP'] % game.owner)
        else:
            bot.notice(STRINGS['NOT_STARTED'], trigger.nick)

    def join(self, bot, trigger):
        if trigger.sender in self.games:
            self.games[trigger.sender].join(bot, trigger)
        else:
            bot.say(STRINGS['NOT_STARTED'])

    def deal(self, bot, trigger):
        if trigger.sender not in self.games:
            bot.say(STRINGS['NOT_STARTED'])
            return
        self.games[trigger.sender].deal(bot, trigger)

    def play(self, bot, trigger):
        if trigger.sender not in self.games:
            return
        game = self.games[trigger.sender]
        winner = game.currentPlayer
        if game.play(bot, trigger) == 'WIN':
            winner = game.playerOrder[winner]
            game_duration = datetime.now() - game.startTime
            hours, remainder = divmod(game_duration.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            game_duration = '%.2d:%.2d:%.2d' % (hours, minutes, seconds)
            bot.say(STRINGS['WIN'] % (winner, game_duration))
            self.gameEnded(bot, trigger, winner)

    def draw(self, bot, trigger):
        if trigger.sender not in self.games:
            return
        game = self.games[trigger.sender]
        game.draw(bot, trigger)

    # this is not a typo, avoiding collision with Python's pass keyword
    def passs(self, bot, trigger):
        if trigger.sender not in self.games:
            return
        game = self.games[trigger.sender]
        game.passs(bot, trigger)

    def sendCards(self, bot, trigger):
        if trigger.sender not in self.games:
            return
        game = self.games[trigger.sender]
        game.sendCards(bot, trigger.nick)

    def sendCounts(self, bot, trigger):
        if trigger.sender not in self.games:
            return
        game = self.games[trigger.sender]
        game.sendCounts(bot)

    def topscores(self, bot):
        scores = self.getScores(bot)
        if not scores:
            bot.say(STRINGS['NO_SCORES'])
            return
        order = sorted(scores.keys(), key=lambda k: scores[k]['points'], reverse=YES)
        i = 1
        for player in order[:5]:
            if not scores[player]['points']:
                # nobody else has any points; stop printing
                break
            bot.say(STRINGS['SCORE_ROW'] %
                    (i, player, scores[player]['points'], scores[player]['games'], scores[player]['wins'],
                     timedelta(seconds=int(scores[player]['playtime']))))
            i += 1

    def gameEnded(self, bot, trigger, winner):
        game = self.games[trigger.sender]
        try:
            score = 0
            for p in game.players:
                for c in game.players[p]:
                    if c[0] == 'W':
                        score += self.special_scores[c]
                    elif c[1] in ['S', 'R', 'D']:
                        score += self.special_scores[c[1:]]
                    else:
                        score += int(c[1])
            bot.say(STRINGS['GAINS'] % (winner, score))
            self.updateScores(bot, game.players.keys(), winner, score,
                              (datetime.now() - game.startTime).seconds)
        except Exception, e:
            print 'Score error: %s' % e
        del self.games[trigger.sender]

    def updateScores(self, bot, players, winner, score, time):
        import sys
        if sys.version_info.major < 3:
            string = unicode
        else:
            string = str
        scores = self.getScores(bot)
        winner = string(winner)
        for pl in players:
            pl = string(pl)
            if pl not in scores:
                scores[pl] = {'games': 0, 'wins': 0, 'points': 0, 'playtime': 0}
            scores[pl]['games'] += 1
            scores[pl]['playtime'] += time
        scores[winner]['wins'] += 1
        scores[winner]['points'] += score
        try:
            scorefile = open(self.scoreFile, 'w')
            json.dump(scores, scorefile)
        except Exception, e:
            bot.say('Error saving UNO score file: %s' % e)

    def getScores(self, bot):
        scores = {}
        try:
            scores = self.loadScores()
        except ValueError:
            try:
                self.convertScorefile(bot)
                scores = self.loadScores()
            except ValueError:
                bot.say('Something has gone horribly wrong with the UNO scores.')
        return scores

    def loadScores(self):
        scorefile = open(self.scoreFile, 'r')
        scores = json.load(scorefile)
        scorefile.close()
        return scores or {}

    def convertScorefile(self, bot):
        scores = {}
        try:
            scorefile = open(self.scoreFile, 'r')
            for line in scorefile:
                tokens = line.replace('\n', '').split(' ')
                if len(tokens) < 4: continue
                if len(tokens) == 4: tokens.append(0)
                scores[tools.Identifier(tokens[0])] = {
                    'games'   : int(tokens[1]),
                    'wins'    : int(tokens[2]),
                    'points'  : int(tokens[3]),
                    'playtime': int(tokens[4]),
                }
            scorefile.close()
        except Exception, e:
            bot.say('Score conversion error: %s' % e)
            pass
        else:
            bot.say('Converted UNO score file to new JSON format.')
        try:
            scorefile = open(self.scoreFile, 'w')
            json.dump(scores, scorefile)
            scorefile.close()
        except Exception, e:
            bot.say('Error converting UNO score file: %s' % e)
            pass
        else:
            bot.say('Wrote UNO score file in new JSON format.')


unobot = UnoBot()


@module.commands('uno')
@module.example('.uno')
@module.priority('high')
@module.require_chanmsg()
def uno(bot, trigger):
    """
    Start UNO in the current channel.
    """
    unobot.start(bot, trigger)


@module.commands('unostop')
@module.example('.unostop')
@module.priority('high')
@module.require_chanmsg()
def unostop(bot, trigger):
    """
    Stops an UNO game in progress.
    """
    unobot.stop(bot, trigger)


@module.rule('^join$')
@module.priority('high')
@module.require_chanmsg()
def join(bot, trigger):
    unobot.join(bot, trigger)


@module.commands('deal')
@module.priority('high')
@module.require_chanmsg()
def deal(bot, trigger):
    unobot.deal(bot, trigger)


@module.commands('play')
@module.priority('high')
@module.require_chanmsg()
def play(bot, trigger):
    unobot.play(bot, trigger)


@module.commands('draw')
@module.priority('high')
@module.require_chanmsg()
def draw(bot, trigger):
    unobot.draw(bot, trigger)


@module.commands('pass')
@module.priority('high')
@module.require_chanmsg()
# this is not a typo, avoiding collision with Python's pass keyword
def passs(bot, trigger):
    unobot.passs(bot, trigger)


@module.commands('cards')
@module.example('.cards')
@module.priority('high')
def cards(bot, trigger):
    unobot.sendCards(bot, trigger)


@module.commands('counts')
@module.example('.counts')
@module.priority('high')
@module.require_chanmsg()
def counts(bot, trigger):
    """
    Sends current UNO card counts to the channel, if a game is in progress.
    """
    unobot.sendCounts(bot, trigger)


@module.commands('unohelp')
@module.example('.unohelp')
@module.priority('high')
def unohelp(bot, trigger):
    """
    Shows some basic help for UNO game-play.
    """
    p = bot.config.core.help_prefix
    r = trigger.nick
    bot.reply('I am sending you UNO help privately. If you do not see it, configure your client to show '
              'non-server notices in the current channel. Cards are sent the same way during game-play.')
    bot.notice('UNO is played using the %splay, %sdraw, and %spass commands.' % (p, p, p), r)
    bot.notice('To play a card, say %splay c f (where c = r/g/b/y and f = the card\'s face value).'
               ' e.g. %splay r 2 to play a red 2 or %splay b d2 to play a blue D2.' % (p, p, p), r)
    bot.notice('Wild (W) and Wild Draw 4 (WD4) cards are played as %splay w[d4] c'
               ' (where c = the color you wish to change the discard pile to).' % p, r)
    bot.notice('If you cannot play a card on your turn, you must %sdraw. If that card is not playable, '
               'you must %spass (forfeiting your turn).' % (p, p), r)


@module.commands('unotop')
@module.example('.unotop')
@module.priority('high')
def unotop(bot, trigger):
    """
    Shows the top 5 players by score. Unlike most UNO commands, can be sent in a PM.
    """
    unobot.topscores(bot)


if __name__ == '__main__':
    print __doc__.strip()
