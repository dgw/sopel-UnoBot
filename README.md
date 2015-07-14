# willie-UnoBot
Port of Tamás Márki's unobot.py for Phenny to Willie 5.x+

## Origins
Original code from http://tmarki.com/wp/2010/02/18/irc-uno-bot-for-phenny/
licensed under the FreeBSD / BSD 2-clause license and copyright Tamás Márki.

The original code was itself a port of a mIRC script, probably the one found
at http://hawkee.com/snippet/5301/

## Changes
This fork includes (but is not limited to including) the following updates:

* Players can now leave a game in progress.
  * Players can also be kicked from a game in progress by the owner or a
    bot admin if necessary.
  * The bot saves the hands of players that leave a game in progress until
    that game is over, to prevent players with large hands from simply doing
    a quit/join cycle to get back down to 7 cards.
* Added `unohelp` command for new players to learn the basics of gameplay
  and use of many UNO commands not included in Willie's `commands` list to
  keep from polluting it too much.
* Added `cards` command for players to have the bot send them their hand
  again in case they were in another channel when their turn came and the
  notice was therefore sent to the wrong window.
* The module now supports a game in each channel, rather than being limited
  to playing UNO in only one channel.
* Score saving uses JSON objects instead of hardcoded format strings. While
  less compact, it is much more easily understood by a human reader, and is
  easier for the bot owner to edit if corrections are needed.
* The "top 10" list has been renamed from `unotop10` to `unotop` and only
  displays five (5) entries to reduce spam to the channel.
* The bot owner can query for a list of channels in which UNO games are
  running (useful as preparation for updates, server maintenance, etc.).
* Use new decorators from Phenny's successor, Willie, soon to be renamed to
  something else, probably for the last time — see #willie @ freenode. This
  project's name will likely change to match Willie's new name when it is
  decided.
* Updated syntax to take advantage of new bot framework features.
  * For example, the bot no longer fails to recognize `play` commands that
    contain extra whitespace between the arguments.
