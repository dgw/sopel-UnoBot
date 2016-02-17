# sopel-UnoBot
Port of Tamás Márki's unobot.py for Phenny to Sopel 5.5+ (formerly known as Willie)

## Origins
Original code from http://tmarki.com/wp/2010/02/18/irc-uno-bot-for-phenny/ licensed under the FreeBSD / BSD 2-clause
license and copyright Tamás Márki.

The original code was itself a port of a mIRC script, probably the one found at http://hawkee.com/snippet/5301/

There is also an unobot.py version maintained within the @myano/jenni repo, but it is as different from this version
as this version is from the code it was built on. A few ideas from that repo may make their way into this one at some
point, but most of the development here up to now was done before discovering the other fork.

## Changes
This fork includes (but is not limited to including) the following updates:

* Players can now leave a game in progress.
  * Players can also be kicked from a game in progress by the owner or a bot admin if necessary.
  * The bot saves the hands of players that leave a game in progress until that game is over, to prevent players with
    large hands from simply doing a quit/join cycle to get back down to 7 cards.
* Added `unohelp` command for new players to learn the basics of gameplay and use of many UNO commands not included in
  Sopel's `commands` list to keep from polluting it too much.
* Added `cards` command for players to have the bot send them their hand again in case they were in another channel
  when their turn came and the notice was therefore sent to the wrong window.
* The module now supports a game in each channel, rather than being limited to playing UNO in only one channel.
  * Games can be moved from channel to channel, as well, by the game owner or a bot admin, so as to allow a flourishing
    discussion in a channel where UNO is being played to continue uninterrupted while the game moves elsewhere.
  * The bot owner can query for a list of channels in which UNO games are running (useful as preparation for updates,
    bot server maintenance, etc.).
* Score saving uses JSON objects instead of hardcoded format strings. While less compact, it is much more easily
  understood by a human reader, and is easier for the bot owner to edit if corrections are needed.
* The "top 10" list has been renamed from `unotop10` to `unotop` and only displays five (5) entries to reduce spam to
  the channel.
* Use new decorators from Phenny's successor, Sopel (formerly known as Willie).
  — see #sopel @ freenode. This project was formerly known as willie-UnoBot and was renamed to match the bot upon being
    updated to support the new version.
* Updated syntax to take advantage of new bot framework features.
  * For example, the bot no longer fails to recognize `play` commands that contain extra whitespace between the arguments.

## Licensing
Parts of this project are covered by the Simplified BSD / FreeBSD / BSD 2-clause license. However, much of it has not
yet been declared licensed. See the LICENSE.md file for details.
