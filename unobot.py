"""
This file is covered under the project license, located in LICENSE.md
"""

import willie.module as module
import willie.tools as tools
from willie.formatting import colors, CONTROL_BOLD, CONTROL_COLOR, CONTROL_NORMAL
import json
import random
import threading
from datetime import datetime, timedelta

SCOREFILE = "/var/lib/willie/unoscores.txt"

YES = WIN = STOP = True
NO = False

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
    'ENOUGH':          "There are enough players to deal now.",
    'NOT_STARTED':     "Game not started.",
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
    'YOUR_RANK':       "%s is ranked #%d with %d accumulated UNO points from %d victories.",
    'NOT_RANKED':      "%s hasn't finished an UNO game, and thus has no rank yet.",
    'SCORE_ROW':       "#%s %s (%d %s in %d %s (%d won), %s wasted)",
    'TOP_CARD':        "%s's turn. Top Card: %s",
    'YOUR_CARDS':      "Your cards (%d): %s",
    'NEXT_START':      "Next: ",
    'SB_START':        "Standings: ",
    'SB_PLAYER':       "%s (%s cards)",
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
                        "dark/light background color, respectively. Use %punotheme default to reset it."]
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
        self.topCard = None
        self.way = 1
        self.drawn = NO
        self.deck = []
        self.startTime = None

    def join(self, bot, trigger):
        if trigger.nick not in self.players:
            self.players[trigger.nick] = []
            with lock:
                self.playerOrder.append(trigger.nick)
            if self.deck:
                if trigger.nick in self.deadPlayers:
                    self.players[trigger.nick] = self.deadPlayers.pop(trigger.nick)
                    bot.say(STRINGS['DEALING_BACK'] % (
                        trigger.nick, self.playerOrder.index(trigger.nick) + 1
                    ))
                    return
                for i in xrange(0, 7):
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
        playernum = self.playerOrder.index(player) + 1
        bot.say(STRINGS['PLAYER_QUIT'] % (player, playernum))
        return self.remove_player(bot, player)

    def kick(self, bot, trigger):
        if trigger.nick != self.owner and not trigger.admin:
            bot.say(STRINGS['CANT_KICK'] % self.owner)
            return
        player = tools.Identifier(trigger.group(3))
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
            for i in xrange(0, 7):
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
        if trigger.nick != self.playerOrder[self.currentPlayer]:
            bot.say(STRINGS['ON_TURN'] % self.playerOrder[self.currentPlayer])
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

            self.inc_player()
            self.card_played(bot, playcard)

            if len(self.players[self.playerOrder[pl]]) == 1:
                bot.say(STRINGS['UNO'] % self.playerOrder[pl])
            elif len(self.players[self.playerOrder[pl]]) == 0:
                return WIN
            self.show_on_turn(bot)

    def draw(self, bot, trigger):
        if not self.deck:
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
        bot.notice(STRINGS['DRAWN_CARD']
                   % self.render_cards([c], UnoBot.get_card_theme(bot, trigger.nick)), trigger.nick)

    def pass_(self, bot, trigger):
        if not self.deck:
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
            bot.say(STRINGS['TOP_CARD'] % (pl, self.render_cards([self.topCard], UnoBot.get_card_theme(bot, pl))))
            self.send_cards(bot, self.playerOrder[self.currentPlayer])
            self.send_next(bot)

    def send_cards(self, bot, who):
        cards = self.players[who]
        bot.notice(STRINGS['YOUR_CARDS']
                   % (len(cards), self.render_cards(cards, UnoBot.get_card_theme(bot, who))), who)

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
                arr.append(STRINGS['SB_PLAYER'] % (self.playerOrder[plr], len(
                    self.players[self.playerOrder[plr]])))
                plr += inc
                if plr == len(self.players) and not full:
                    plr = 0
                if plr < 0:
                    plr = len(self.players) - 1
        return ' - '.join(arr)

    @staticmethod
    def render_cards(cards, theme=THEME_NONE):
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
            if 'D2' in card:
                bot.say(STRINGS['D2'] % self.playerOrder[self.currentPlayer])
                z = [self.get_card(), self.get_card()]
                bot.notice(STRINGS['CARDS'] % self.render_cards(z, UnoBot.get_card_theme(bot, self.playerOrder[
                    self.currentPlayer])), self.playerOrder[self.currentPlayer])
                self.players[self.playerOrder[self.currentPlayer]].extend(z)
                self.inc_player()
            elif 'WD4' in card:
                bot.say(STRINGS['WD4'] % self.playerOrder[self.currentPlayer])
                z = [self.get_card(), self.get_card(), self.get_card(),
                     self.get_card()]
                bot.notice(STRINGS['CARDS'] % self.render_cards(z, UnoBot.get_card_theme(bot, self.playerOrder[
                    self.currentPlayer])), self.playerOrder[self.currentPlayer])
                self.players[self.playerOrder[self.currentPlayer]].extend(z)
                self.inc_player()
            elif 'S' in card:
                bot.say(STRINGS['SKIPPED'] % self.playerOrder[self.currentPlayer])
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
            player = trigger.group(3) or trigger.nick
            try:
                rank = order.index(player) + 1
            except ValueError:
                bot.say(STRINGS['NOT_RANKED'] % player)
                return
            bot.say(STRINGS['YOUR_RANK'] % (player, rank, scores[player]['points'], scores[player]['wins']))

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
        import sys
        if sys.version_info.major < 3:
            string = unicode
        else:
            string = str
        with lock:
            scores = self.get_scores(bot)
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


if __name__ == '__main__':
    print __doc__.strip()
