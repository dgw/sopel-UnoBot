"""
This file is covered under the project license, located in LICENSE.md
"""

import willie.module as module
import willie.tools as tools
from willie.formatting import colors, CONTROL_BOLD, CONTROL_COLOR, CONTROL_NORMAL
import json
import random
import sys
import threading
from datetime import datetime, timedelta

# niceties for Python 2 / 3 compatibility
if sys.version_info.major < 3:
    range = xrange
    str = unicode

SCOREFILE = "/var/lib/willie/unoscores.txt"
DECK_SIZE = 7
MINIMUM_HAND_FOR_JOIN = 5

YES = WIN = STOP = True
NO = False

COLORS_ON = 1
COLORS_OFF = 0

THEME_NONE = 0
THEME_DARK = 1
THEME_LIGHT = 2
THEMES = {
    'default': THEME_NONE,
    'dark':    THEME_DARK,
    'light':   THEME_LIGHT,
}
THEME_NAMES = dict((v, n) for (n, v) in THEMES.items())

lock = threading.RLock()

STRINGS = {
    'ALREADY_STARTED': "Game already started by %s! Type join to join!",
    'GAME_STARTED':    "IRC-UNO started by %s - Type join to join!",
    'GAME_STOPPED':    "Game stopped.",
    'CANT_STOP':       "%s is the game owner, you can't stop it!",
    'DEALING_IN':      "Dealing %s into the game as player #%s!",
    'DEALING_BACK':    "Here, %s, I saved your cards. You're back in the game as player #%s.",
    'JOINED':          "Dealing %s into the game as player #%s!",
    'CANT_JOIN':       "Can't join you to this game, %s. Wait for the next one.",
    'NICK_CHANGED':    "Followed your nick change from %s to %s. You're still in the %s UNO game!",
    'NOT_PLAYING':     "You aren't a player in this UNO game!",
    'ENOUGH':          "There are enough players to deal now.",
    'NOT_STARTED':     "Game not started.",
    'NOT_IN_CHANNEL':  "I'm not in %s, so I can't move the game there.",
    'NEED_CHANNEL':    "I need a channel name to move to.",
    'CANT_MOVE':       "Only %s can move the game.",
    'CHANNEL_IN_USE':  "Channel %s already has an UNO game in progress.",
    'GAME_MOVED':      "%s UNO game moved to %s.",
    'MOVED_FROM':      "Note: %s moved an UNO here from %s.",
    'NOT_ENOUGH':      "Not enough players to deal yet.",
    'NEEDS_TO_DEAL':   "%s needs to deal.",
    'ALREADY_DEALT':   "Already dealt.",
    'ON_TURN':         "It's %s's turn.",
    'DONT_HAVE':       "You don't have that card!",
    'DOESNT_PLAY':     "That card can't be played now.",
    'UNO':             "UNO! %s has ONE card left!",
    'WIN':             "We have a winner: %s!!! This game took %s",
    'DRAWN_ALREADY':   "You've already drawn, either play or pass.",
    'DRAWN_CARD':      "You drew: %s",
    'DRAW_FIRST':      "You have to draw first.",
    'PASSED':          "%s passed!",
    'NO_SCORES':       "No scores yet",
    'YOUR_RANK':       "%s is ranked #%d in UNO, having accumulated %d %s from %d %s.",
    'NOT_RANKED':      "%s hasn't finished an UNO game, and thus has no rank yet.",
    'SCORE_ROW':       "#%s %s (%d %s in %d %s (%d won), %s wasted)",
    'TOP_CARD':        "%s's turn. Top Card: %s",
    'YOUR_CARDS':      "Your cards (%d): %s",
    'NEXT_START':      "Next: ",
    'SB_START':        "Standings: ",
    'SB_PLAYER':       "%s (%d %s)",
    'D2':              "%s draws two and is skipped!",
    'CARDS':           "Cards: %s",
    'WD4':             "%s draws four and is skipped!",
    'SKIPPED':         "%s is skipped!",
    'REVERSED':        "Order reversed!",
    'GAINS':           "%s gains %s points!",
    'PLAYER_QUIT':     "Removing %s (player #%d) from the current UNO game.",
    'PLAYER_KICK':     "Kicking %s (player #%d) from the game at %s's request.",
    'OWNER_LEFT':      "Game owner left! New owner: %s",
    'CANT_KICK':       "Only %s or a bot admin can kick players from the game.",
    'CANT_CONTINUE':   "You need at least two people to play UNO. RIP.",
    'BAD_COLOR_OPT':   "You must specify on or off for card colors.",
    'COLOR_SET_ON':    "Will use color codes for %s.",
    'COLOR_SET_OFF':   "Will print colors for %s.",
    'THEME_CURRENT':   "You are currently using the %s card theme.",
    'THEME_NEEDED':    "You must specify one of the available themes: %s",
    'THEME_SET':       "Set %s to use the %s card theme.",
    'HELP_INTRO':      "I am sending you UNO help privately. If you do not see it, configure your client to show "
                       "non-server notices in the current channel. Cards are sent the same way during game-play.",
    'HELP_LINES':      ["UNO is played using the %pplay, %pdraw, and %ppass commands.",
                        "To play a card, say %pplay c f (where c = r/g/b/y and f = the card's face value). e.g. "
                        "%pplay r 2 to play a red 2 or %pplay b d2 to play a blue D2.",
                        "Wild (W) and Wild Draw 4 (WD4) cards are played as %pplay w[d4] c (where c = the color you "
                        "wish to change the discard pile to).",
                        "If you cannot play a card on your turn, you must %pdraw. If that card is not playable, you "
                        "must %ppass (forfeiting your turn).",
                        "Use %punotheme (dark|light) if you are having trouble reading your cards to give them a "
                        "dark/light background color, respectively. Use %punotheme default to reset it.",
                        "Alternatively, do %punocolors off to use an alternate presentation format that doesn't "
                        "use color codes at all."],
    'PLAY_SYNTAX':      "Command syntax error. You must use e.g. %pplay r 3 or %pplay w y.",
}  # yapf: disable
COLORED_CARD_NUMS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'R', 'S', 'D2']
CARD_COLORS = 'RGBY'
SPECIAL_CARDS = ['W', 'WD4']


class UnoGame:
    def __init__(self, trigger):
        self.owner = trigger.nick
        self.channel = trigger.sender
        self.deck = []
        self.players = {self.owner: []}
        self.deadPlayers = {}
        self.playerOrder = [self.owner]
        self.currentPlayer = 0
        self.previousPlayer = None
        self.topCard = None
        self.way = 1
        self.drawn = NO
        self.smallestHand = DECK_SIZE
        self.unoCalled = NO
        self.deck = []
        self.startTime = None

    def join(self, bot, trigger):
        with lock:
            if trigger.nick not in self.players:
                if self.smallestHand < MINIMUM_HAND_FOR_JOIN and trigger.nick not in self.deadPlayers:
                    bot.say(STRINGS['CANT_JOIN'] % trigger.nick)
                    return
                self.players[trigger.nick] = []
                self.playerOrder.append(trigger.nick)
                if self.deck:
                    if trigger.nick in self.deadPlayers:
                        self.players[trigger.nick] = self.deadPlayers.pop(trigger.nick)
                        bot.say(STRINGS['DEALING_BACK'] % (
                            trigger.nick, self.playerOrder.index(trigger.nick) + 1
                        ))
                        return
                    for i in range(0, DECK_SIZE):
                        self.players[trigger.nick].append(self.get_card())
                    bot.say(STRINGS['DEALING_IN'] % (
                        trigger.nick, self.playerOrder.index(trigger.nick) + 1
                    ))
                else:
                    bot.say(STRINGS['JOINED'] % (
                        trigger.nick, self.playerOrder.index(trigger.nick) + 1
                    ))
                    if len(self.players) > 1:
                        bot.notice(STRINGS['ENOUGH'], self.owner)

    def quit(self, bot, trigger):
        player = trigger.nick
        if player not in self.players:
            return
        with lock:
            playernum = self.playerOrder.index(player) + 1
            bot.say(STRINGS['PLAYER_QUIT'] % (player, playernum))
            return self.remove_player(bot, player)

    def kick(self, bot, trigger):
        if trigger.nick != self.owner and not trigger.admin:
            bot.say(STRINGS['CANT_KICK'] % self.owner)
            return
        player = tools.Identifier(trigger.group(3))
        with lock:
            if player not in self.players:
                return
            if player == trigger.nick:
                return self.quit(bot, trigger)
            playernum = self.playerOrder.index(player) + 1
            bot.say(STRINGS['PLAYER_KICK'] % (player, playernum, trigger.nick))
            return self.remove_player(bot, player)

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
        with lock:
            self.startTime = datetime.now()
            self.deck = self.create_deck()
            for i in range(0, DECK_SIZE):
                for p in self.players:
                    self.players[p].append(self.get_card())
            self.topCard = self.get_card()
            while self.topCard in ['W', 'WD4']:
                self.topCard = self.get_card()
            self.currentPlayer = 1
            self.card_played(bot, self.topCard)
            self.show_on_turn(bot)

    def play(self, bot, trigger):
        if not self.deck:
            return
        if trigger.nick not in self.players:
            bot.notice(STRINGS['NOT_PLAYING'], trigger.nick)
            return
        if trigger.nick != self.playerOrder[self.currentPlayer]:
            bot.say(STRINGS['ON_TURN'] % self.playerOrder[self.currentPlayer])
            return
        if not trigger.group(3) or not trigger.group(4):
            bot.notice(STRINGS['PLAY_SYNTAX'].replace('%p', bot.config.core.help_prefix), trigger.nick)
            return
        color = trigger.group(3).upper()
        if color in CARD_COLORS:
            card = trigger.group(4).upper()
            searchcard = color + card
        elif color in SPECIAL_CARDS:
            card = color
            color = trigger.group(4).upper()
            searchcard = card
        else:
            return

        with lock:
            pl = self.currentPlayer
            if searchcard not in self.players[self.playerOrder[pl]]:
                bot.notice(STRINGS['DONT_HAVE'], self.playerOrder[pl])
                return
            playcard = color + card
            if not self.card_playable(playcard):
                bot.notice(STRINGS['DOESNT_PLAY'],
                           self.playerOrder[pl])
                return
            self.drawn = NO
            self.players[self.playerOrder[pl]].remove(searchcard)
            hand_size = len(self.players[self.playerOrder[pl]])
            if hand_size < self.smallestHand:
                self.smallestHand = hand_size

            self.inc_player()
            self.card_played(bot, playcard)

            if len(self.players[self.playerOrder[pl]]) == 1:
                bot.say(STRINGS['UNO'] % self.playerOrder[pl])
            elif len(self.players[self.playerOrder[pl]]) == 0:
                return WIN
            self.show_on_turn(bot)

    def call_uno(self, bot, trigger):
        caller = trigger.nick
        with lock:
            if len(self.players[caller]) != 1:
                z = [self.get_card(), self.get_card()]
                self.players[caller].extend(z)
                bot.notice(STRINGS['DRAWN_CARD'] % self.render_cards(bot, z, caller), caller)
            else:
                self.unoCalled = caller

    def draw(self, bot, trigger):
        if not self.deck:
            return
        if trigger.nick not in self.players:
            bot.notice(STRINGS['NOT_PLAYING'], trigger.nick)
            return
        if trigger.nick != self.playerOrder[self.currentPlayer]:
            bot.say(STRINGS['ON_TURN'] % self.playerOrder[self.currentPlayer])
            return
        with lock:
            if self.drawn:
                bot.notice(STRINGS['DRAWN_ALREADY'],
                           self.playerOrder[self.currentPlayer])
                return
            self.drawn = YES
            c = self.get_card()
            self.players[self.playerOrder[self.currentPlayer]].append(c)
        bot.notice(STRINGS['DRAWN_CARD'] % self.render_cards(bot, [c], trigger.nick), trigger.nick)

    def pass_(self, bot, trigger):
        if not self.deck:
            return
        if trigger.nick not in self.players:
            bot.notice(STRINGS['NOT_PLAYING'], trigger.nick)
            return
        with lock:
            if trigger.nick != self.playerOrder[self.currentPlayer]:
                bot.say(STRINGS['ON_TURN'] % self.playerOrder[self.currentPlayer])
                return
            if not self.drawn:
                bot.notice(STRINGS['DRAW_FIRST'],
                           self.playerOrder[self.currentPlayer])
                return
            self.drawn = NO
            bot.say(STRINGS['PASSED'] % self.playerOrder[self.currentPlayer])
            self.inc_player()
        self.show_on_turn(bot)

    def show_on_turn(self, bot):
        with lock:
            pl = self.playerOrder[self.currentPlayer]
            bot.say(STRINGS['TOP_CARD'] % (pl, self.render_cards(bot, [self.topCard], pl)))
            self.send_cards(bot, self.playerOrder[self.currentPlayer])
            self.send_next(bot)

    def send_cards(self, bot, who):
        if who not in self.players:
            bot.notice(STRINGS['NOT_PLAYING'], who)
            return
        cards = self.players[who]
        bot.notice(STRINGS['YOUR_CARDS'] % (len(cards), self.render_cards(bot, cards, who)), who)

    def send_next(self, bot):
        with lock:
            bot.notice(STRINGS['NEXT_START'] + self.render_counts(), self.playerOrder[self.currentPlayer])

    def send_counts(self, bot):
        if self.startTime:
            bot.say(STRINGS['SB_START'] + self.render_counts(YES))
        else:
            bot.say(STRINGS['NOT_STARTED'])

    def render_counts(self, full=NO):
        with lock:
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
                cards = len(self.players[self.playerOrder[plr]])
                g_cards = "card" if cards == 1 else "cards"
                arr.append(STRINGS['SB_PLAYER'] % (self.playerOrder[plr], cards, g_cards))
                plr += inc
                if plr == len(self.players) and not full:
                    plr = 0
                if plr < 0:
                    plr = len(self.players) - 1
        return ' - '.join(arr)

    @staticmethod
    def render_cards(bot, cards, who):
        if UnoBot.get_card_colors(bot, who):
            return UnoGame.render_cards_colored(cards, UnoBot.get_card_theme(bot, who))
        else:
            return UnoGame.render_cards_nocolor(cards)

    @staticmethod
    def render_cards_nocolor(cards):
        ret = []
        for card in sorted(cards):
            if card[0] == 'W':
                ret.append('[W]')
                continue
            ret.append('%s[%s]' % (card[0], card[1:]))
        return ' '.join(ret)

    @staticmethod
    def render_cards_colored(cards, theme=THEME_NONE):
        card_tmpl = CONTROL_COLOR + '%s%s[%s]'
        background = ''
        bold = ''
        blue_code = colors.LIGHT_BLUE
        green_code = colors.LIGHT_GREEN
        red_code = colors.RED
        yellow_code = colors.YELLOW
        wild_code = colors.BLACK
        if theme:
            if theme == THEME_DARK:
                background = ',' + colors.BLACK
                bold = CONTROL_BOLD
                wild_code = colors.LIGHT_GREY
            elif theme == THEME_LIGHT:
                background = ',' + colors.LIGHT_GREY
                bold = CONTROL_BOLD
                green_code = colors.GREEN
                yellow_code = colors.ORANGE
        ret = []
        for card in sorted(cards):
            if card in ['W', 'WD4']:
                ret.append(card_tmpl % (wild_code, background, card))
                continue
            if 'W' in card:
                card = card[0] + '*'
            color_code = ''
            if card[0] == 'B':
                color_code = blue_code
            if card[0] == 'G':
                color_code = green_code
            if card[0] == 'R':
                color_code = red_code
            if card[0] == 'Y':
                color_code = yellow_code
            t = card_tmpl % (color_code, background, card[1:])
            ret.append(t)
        return bold + ''.join(ret) + CONTROL_NORMAL

    def card_playable(self, card):
        if 'W' in card and card[0] in CARD_COLORS:
            return True
        with lock:
            if 'W' in self.topCard:
                return card[0] == self.topCard[0]
            return ((card[0] == self.topCard[0]) or
                    (card[1] == self.topCard[1])) and ('W' not in card)

    def card_played(self, bot, card):
        with lock:
            pl = self.playerOrder[self.currentPlayer]
            if 'D2' in card:
                bot.say(STRINGS['D2'] % pl)
                z = [self.get_card(), self.get_card()]
                bot.notice(STRINGS['CARDS'] % self.render_cards(bot, z, pl), pl)
                self.players[pl].extend(z)
                self.inc_player()
            elif 'WD4' in card:
                bot.say(STRINGS['WD4'] % pl)
                z = [self.get_card(), self.get_card(), self.get_card(),
                     self.get_card()]
                bot.notice(STRINGS['CARDS'] % self.render_cards(bot, z, pl), pl)
                self.players[pl].extend(z)
                self.inc_player()
            elif 'S' in card:
                bot.say(STRINGS['SKIPPED'] % pl)
                self.inc_player()
            elif card[1] == 'R' and 'W' not in card:
                bot.say(STRINGS['REVERSED'])
                self.way = -self.way
                self.inc_player()
                self.inc_player()
            self.topCard = card

    def get_card(self):
        with lock:
            ret = self.deck.pop(0)
            if not self.deck:
                self.deck = self.create_deck()
        return ret

    @staticmethod
    def create_deck():
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

    def inc_player(self):
        with lock:
            self.previousPlayer = self.currentPlayer
            self.currentPlayer += self.way
            if self.currentPlayer == len(self.players):
                self.currentPlayer = 0
            if self.currentPlayer < 0:
                self.currentPlayer = len(self.players) - 1

    def remove_player(self, bot, player):
        if len(self.players) == 1:
            return STOP
        if player not in self.players:
            return
        with lock:
            pl = self.playerOrder.index(player)
            self.deadPlayers[player] = self.players.pop(player)
            self.playerOrder.remove(player)
            if self.startTime:
                if player == self.owner:
                    self.owner = self.playerOrder[0]
                    if len(self.players) > 1:
                        bot.say(STRINGS['OWNER_LEFT'] % self.owner)
                    else:
                        return STOP
                if self.way < 0 and pl <= self.currentPlayer:
                    self.inc_player()
                elif pl < self.currentPlayer:
                    self.way *= -1
                    self.inc_player()
                    self.way *= -1
                if self.currentPlayer >= len(self.playerOrder):
                    self.currentPlayer = 0
                if self.currentPlayer < 0:
                    self.currentPlayer = len(self.playerOrder) - 1
                if len(self.players) > 1:
                    self.show_on_turn(bot)
                else:
                    return STOP
            else:
                if player == self.owner:
                    self.owner = self.playerOrder[0]
                    bot.say(STRINGS['OWNER_LEFT'] % self.owner)

    def nick_change(self, bot, trigger):
        old = trigger.nick
        new = tools.Identifier(trigger)
        if old not in self.players:
            return
        with lock:
            idx = self.playerOrder.index(old)
            self.players[new] = self.players.pop(old)
            self.playerOrder[idx] = new
            if self.owner == old:
                self.owner = new
            bot.notice(STRINGS['NICK_CHANGED'] % (old, new, self.channel), new)

    def game_moved(self, bot, who, oldchan, newchan):
        with lock:
            self.channel = newchan
            bot.msg(self.channel, STRINGS['MOVED_FROM'] % (who, oldchan))
            for player in self.players:
                bot.notice(STRINGS['GAME_MOVED'] % (oldchan, newchan), player)


class UnoBot:
    def __init__(self):
        self.special_scores = {'R': 20, 'S': 20, 'D2': 20, 'WD4': 50, 'W': 50}
        self.scoreFile = SCOREFILE
        self.games = {}

    def start(self, bot, trigger):
        if trigger.sender in self.games:
            bot.say(STRINGS['ALREADY_STARTED'] % self.games[trigger.sender].owner)
        else:
            self.games[trigger.sender] = UnoGame(trigger)
            bot.say(STRINGS['GAME_STARTED'] % self.games[trigger.sender].owner)

    def stop(self, bot, trigger, forced=NO):
        if trigger.sender in self.games:
            game = self.games[trigger.sender]
            if trigger.nick == game.owner or trigger.admin or forced:
                if not forced:
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

    def quit(self, bot, trigger):
        if trigger.sender in self.games:
            game = self.games[trigger.sender]
            if game.quit(bot, trigger) == STOP:
                bot.say(STRINGS['CANT_CONTINUE'])
                self.stop(bot, trigger, forced=YES)
        else:
            return

    def kick(self, bot, trigger):
        if trigger.sender in self.games:
            game = self.games[trigger.sender]
            if game.kick(bot, trigger) == STOP:
                bot.say(STRINGS['CANT_CONTINUE'])
                self.stop(bot, trigger, forced=YES)
        else:
            return

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
        if game.play(bot, trigger) == WIN:
            winner = game.playerOrder[winner]
            game_duration = datetime.now() - game.startTime
            hours, remainder = divmod(game_duration.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            game_duration = '%.2d:%.2d:%.2d' % (hours, minutes, seconds)
            bot.say(STRINGS['WIN'] % (winner, game_duration))
            self.game_ended(bot, trigger, winner)

    def call_uno(self, bot, trigger):
        if trigger.sender not in self.games:
            return
        self.games[trigger.sender].call_uno(bot, trigger)

    def draw(self, bot, trigger):
        if trigger.sender not in self.games:
            return
        game = self.games[trigger.sender]
        game.draw(bot, trigger)

    def pass_(self, bot, trigger):
        if trigger.sender not in self.games:
            return
        game = self.games[trigger.sender]
        game.pass_(bot, trigger)

    def send_cards(self, bot, trigger):
        if trigger.sender not in self.games:
            return
        game = self.games[trigger.sender]
        game.send_cards(bot, trigger.nick)

    def send_counts(self, bot, trigger):
        if trigger.sender not in self.games:
            return
        game = self.games[trigger.sender]
        game.send_counts(bot)

    def rankings(self, bot, trigger, toplist=NO):
        scores = self.get_scores(bot)
        if not scores:
            bot.say(STRINGS['NO_SCORES'])
            return
        order = sorted(scores.keys(), key=lambda k: scores[k]['points'], reverse=YES)
        if toplist:
            i = 1
            for player in order[:5]:
                if not scores[player]['points']:
                    break  # nobody else has any points; stop printing
                g_points = "point" if scores[player]['points'] == 1 else "points"
                g_games = "game" if scores[player]['games'] == 1 else "games"
                bot.say(STRINGS['SCORE_ROW'] %
                        (i, player, scores[player]['points'], g_points, scores[player]['games'], g_games,
                         scores[player]['wins'], timedelta(seconds=int(scores[player]['playtime']))))
                i += 1
        else:
            player = str(trigger.group(3) or trigger.nick)
            try:
                rank = order.index(player) + 1
            except ValueError:
                bot.say(STRINGS['NOT_RANKED'] % player)
                return
            points = scores[player]['points']
            g_points = "point" if points == 1 else "points"
            wins = scores[player]['wins']
            g_wins = "victory" if wins == 1 else "victories"
            bot.say(STRINGS['YOUR_RANK'] % (player, rank, points, g_points, wins, g_wins))

    def game_ended(self, bot, trigger, winner):
        with lock:
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
                self.update_scores(bot, game.players.keys(), winner, score,
                                   (datetime.now() - game.startTime).seconds)
            except Exception, e:
                bot.say("UNO score error: %s" % e)
            del self.games[trigger.sender]

    def update_scores(self, bot, players, winner, score, time):
        with lock:
            scores = self.get_scores(bot)
            winner = str(winner)
            for pl in players:
                pl = str(pl)
                if pl not in scores:
                    scores[pl] = {'games': 0, 'wins': 0, 'points': 0, 'playtime': 0}
                scores[pl]['games'] += 1
                scores[pl]['playtime'] += time
            scores[winner]['wins'] += 1
            scores[winner]['points'] += score
            try:
                with open(self.scoreFile, 'w+') as scorefile:
                    json.dump(scores, scorefile)
            except Exception, e:
                bot.say("Error saving UNO score file: %s" % e)

    def get_scores(self, bot):
        scores = {}
        try:
            scores = self.load_scores(bot)
        except ValueError:
            try:
                self.convert_score_file(bot)
                scores = self.load_scores(bot)
            except ValueError:
                bot.say("Something has gone horribly wrong with the UNO scores.")
        return scores

    def load_scores(self, bot):
        scores = {}
        with lock:
            try:
                with open(self.scoreFile, 'r+') as scorefile:
                    scores = json.load(scorefile)
            except ValueError, e:
                bot.say("Error loading UNO scores: %s" % e)
            except IOError, e:
                bot.say("Error opening UNO scores: %s" % e)
        return scores

    def convert_score_file(self, bot):
        scores = {}
        with lock:
            try:
                with open(self.scoreFile, 'r+') as scorefile:
                    for line in scorefile:
                        tokens = line.replace('\n', '').split(' ')
                        if len(tokens) < 4:
                            continue
                        if len(tokens) == 4:
                            tokens.append(0)
                        scores[tools.Identifier(tokens[0])] = {
                            'games':    int(tokens[1]),
                            'wins':     int(tokens[2]),
                            'points':   int(tokens[3]),
                            'playtime': int(tokens[4]),
                        }
            except Exception, e:
                bot.say("Score conversion error: %s" % e)
                return
            else:
                bot.say("Converted UNO score file to new JSON format.")
            try:
                with open(self.scoreFile, 'w+') as scorefile:
                    json.dump(scores, scorefile)
            except Exception, e:
                bot.say("Error converting UNO score file: %s" % e)
            else:
                bot.say("Wrote UNO score file in new JSON format.")

    @staticmethod
    def set_card_colors(bot, trigger):
        setting = trigger.group(3).lower() or None
        if not setting or setting not in ['on', 'off', 'yes', 'no']:
            bot.reply(STRINGS['BAD_COLOR_OPT'])
            return
        if setting in ['on', 'yes']:
            setting = COLORS_ON
            bot.say(STRINGS['COLOR_SET_ON'] % trigger.nick)
        elif setting in ['off', 'no']:
            setting = COLORS_OFF
            bot.say(STRINGS['COLOR_SET_OFF'] % trigger.nick)
        bot.db.set_nick_value(trigger.nick, 'uno_colors', setting)

    @staticmethod
    def get_card_colors(bot, nick):
        ret = bot.db.get_nick_value(nick, 'uno_colors')
        if ret is None:
            return COLORS_ON
        return ret

    @staticmethod
    def set_card_theme(bot, trigger):
        theme = trigger.group(3) or None
        if not theme:
            theme = UnoBot.get_card_theme(bot, trigger.nick)
            bot.say(STRINGS['THEME_CURRENT'] % THEME_NAMES[theme])
            return
        theme = theme.lower()
        if theme not in THEMES:
            bot.say(STRINGS['THEME_NEEDED'] % ', '.join(THEMES.keys()))
            return
        bot.db.set_nick_value(trigger.nick, 'uno_theme', THEMES[theme])
        bot.say(STRINGS['THEME_SET'] % (trigger.nick, theme))

    @staticmethod
    def get_card_theme(bot, nick):
        return bot.db.get_nick_value(tools.Identifier(nick), 'uno_theme') or THEME_NONE

    def nick_change(self, bot, trigger):
        for game in self.games:
            self.games[game].nick_change(bot, trigger)

    def move_game(self, bot, trigger):
        who = trigger.nick
        oldchan = trigger.sender
        newchan = tools.Identifier(trigger.group(3))
        if newchan[0] != '#':
            newchan = tools.Identifier('#' + newchan)
        if oldchan not in self.games:
            bot.reply(STRINGS['NOT_STARTED'])
            return
        owner = self.games[oldchan].owner
        if trigger.admin or who == owner:
            if not newchan:
                bot.reply(STRINGS['NEED_CHANNEL'])
                return
            if newchan == oldchan:
                return
            if newchan.lower() not in bot.privileges:
                bot.reply(STRINGS['NOT_IN_CHANNEL'] % newchan)
                return
            if newchan in self.games:
                bot.reply(STRINGS['CHANNEL_IN_USE'] % newchan)
                return
            game = self.games.pop(oldchan)
            self.games[newchan] = game
            game.game_moved(bot, who, oldchan, newchan)
        else:
            bot.reply(STRINGS['CANT_MOVE'] % owner)


unobot = UnoBot()


@module.commands('uno')
@module.example(".uno")
@module.priority('high')
@module.require_chanmsg
def unostart(bot, trigger):
    """
    Start UNO in the current channel.
    """
    unobot.start(bot, trigger)


@module.commands('unostop')
@module.example(".unostop")
@module.priority('high')
@module.require_chanmsg
def unostop(bot, trigger):
    """
    Stops an UNO game in progress.
    """
    unobot.stop(bot, trigger)


@module.rule('^join$')
@module.priority('high')
@module.require_chanmsg
def unojoin(bot, trigger):
    unobot.join(bot, trigger)


@module.rule('^quit$')
@module.priority('high')
@module.require_chanmsg
def unoquit(bot, trigger):
    unobot.quit(bot, trigger)


@module.commands('unokick')
@module.priority('high')
@module.require_chanmsg
def unokick(bot, trigger):
    unobot.kick(bot, trigger)


@module.commands('deal')
@module.priority('high')
@module.require_chanmsg
def unodeal(bot, trigger):
    unobot.deal(bot, trigger)


@module.commands('play')
@module.priority('high')
@module.require_chanmsg
def unoplay(bot, trigger):
    unobot.play(bot, trigger)


@module.rule('^uno!?$')
@module.priority('high')
@module.require_chanmsg
def unocalled(bot, trigger):
    unobot.call_uno(bot, trigger)


@module.commands('draw')
@module.priority('high')
@module.require_chanmsg
def unodraw(bot, trigger):
    unobot.draw(bot, trigger)


@module.commands('pass')
@module.priority('high')
@module.require_chanmsg
def unopass(bot, trigger):
    unobot.pass_(bot, trigger)


@module.commands('cards')
@module.example(".cards")
@module.priority('high')
@module.require_chanmsg
def unocards(bot, trigger):
    """
    Retrieve your current UNO hand for the current channel's game.
    """
    unobot.send_cards(bot, trigger)


@module.commands('counts')
@module.example(".counts")
@module.priority('high')
@module.require_chanmsg
def unocounts(bot, trigger):
    """
    Sends current UNO card counts to the channel, if a game is in progress.
    """
    unobot.send_counts(bot, trigger)


@module.commands('unocolor', 'unocolour', 'unocolors', 'unocolours')
@module.example(".unocolor off")
@module.priority('low')
def unocolor(bot, trigger):
    """
    Set colored cards on or off. Disabling color will present cards in an alternate format.
    """
    unobot.set_card_colors(bot, trigger)


@module.commands('unotheme')
@module.example(".unotheme dark")
@module.priority('high')
def unotheme(bot, trigger):
    """
    Sets your UNO card theme to have a dark/light background. Clear your theme setting with "default".
    """
    UnoBot.set_card_theme(bot, trigger)


@module.commands('unohelp')
@module.example(".unohelp")
@module.priority('high')
def unohelp(bot, trigger):
    """
    Shows some basic help for UNO game-play.
    """
    p = bot.config.core.help_prefix
    r = trigger.nick
    bot.reply(STRINGS['HELP_INTRO'])
    for line in STRINGS['HELP_LINES']:
        bot.notice(line.replace('%p', p), trigger.nick)


@module.commands('unotop')
@module.example(".unotop")
@module.priority('high')
def unotop(bot, trigger):
    """
    Shows the top 5 players by score. Unlike most UNO commands, can be sent in a PM.
    """
    unobot.rankings(bot, trigger, YES)


@module.commands('unorank')
@module.example(".unorank")
@module.example(".unorank UnoAddict")
@module.priority('high')
def unorank(bot, trigger):
    """
    Shows the ranking, by accumulated UNO points, of the calling player or the specified nick.
    """
    unobot.rankings(bot, trigger, NO)


@module.commands('unogames')
@module.priority('high')
@module.require_admin
def unogames(bot, trigger):
    chans = []
    active = 0
    pending = 0
    with lock:
        for chan in unobot.games.keys():
            if unobot.games[chan].startTime:
                chans.append(chan)
                active += 1
            else:
                chans.append(chan + " (pending)")
                pending += 1
    if not len(chans):
        bot.say('No UNO games in progress, %s.' % trigger.nick)
        return
    g_active = "channel" if active == 1 else "channels"
    g_pending = "channel" if pending == 1 else "channels"
    chanlist = ", ".join(chans[:-2] + [" and ".join(chans[-2:])])
    bot.reply(
        "UNO is pending deal in %d %s and in progress in %d %s: %s." % (pending, g_pending, active, g_active, chanlist))


@module.commands('unomove')
@module.priority('high')
@module.example('.unomove #anotherchannel')
def unomove(bot, trigger):
    """
    Lets the game owner or a bot admin move an UNO game from one channel to another,
    assuming there's no game happening in that channel.
    """
    unobot.move_game(bot, trigger)


# Track nick changes
@module.event('NICK')
@module.rule('.*')
def uno_glue(bot, trigger):
    unobot.nick_change(bot, trigger)


if __name__ == '__main__':
    print __doc__.strip()
