# quotes.py: quote bot
# -*- coding: utf-8 -*-
import pylinkirc
from pylinkirc import utils, world, conf
from pylinkirc.log import log
from pylinkirc.coremods import permissions

import itertools
from sqlalchemy import *
from sqlalchemy.sql import *
from collections import *

import random

##
#
#  Config
#
##

use_mode = conf.conf.get("quote", {}).get("mode", "testing")

config_url = conf.conf.get("quote", {}).get("db", "")
engine = create_engine(config_url)
meta = MetaData()
meta.reflect(bind=engine)
dbc = Table("channels", meta, autoload=True, autoload_with=engine)
dbq = Table("quote", meta, autoload=True, autoload_with=engine)
dbcd = Table("channel_data", meta, autoload=True, autoload_with=engine)

desc = "Quote bot, stores channel quotes."
quote = utils.registerService("quote", desc=desc)
reply = quote.reply
error = quote.error
default_permissions = {"$ircop": ['quotes.admin']}
##
#
#  End Config
#
####
#
#  Helper Functions
#
##
def format(info, chan=None):
    format_string = ""
    channel = info["channel"]
    if chan:
        format_string = "Quote #%(id)s | \"%(quote)s\" added by %(added_by)s/%(channel)s [%(added)s]" % info
    else:
        format_string = "Quote #%(id)s | \"%(quote)s\" added by %(added_by)s [%(added)s]" % info
    return format_string

def is_int(s):
    try:
        int(s)
        return True
    except:
        return False

# Thanks to freenode/#python"s altendky for this.
def squishids(ids):
    if ids == []:
        return "0"
    else:
        found = [[ids[0]]]
        log.info("Found: %s" % found)
        for previous, next in itertools.zip_longest(ids, ids[1:]):
            if next != previous + 1:
                if previous != found[-1][0]:
                    found[-1].append(previous)
                if next is not None:
                    found.append([next])

        return ", ".join("-".join(str(r) for r in f) for f in found)
##
#
#  End Helper Functions
#
####
#
#  Join channels
#
##

if use_mode == "production":
    log.info("\x0303Production mode enabled.")
    chans = []
    channels = engine.execute(select([dbc.c.channel]).where(
        dbc.c.mode == "production"
    )).fetchall()
    for channel in channels:
        chans.append(channel[0])
    newchans = set(chans)
    quote.extra_channels["ecode"] |= newchans
    allchans = quote.extra_channels["ecode"]
    quote.join("ecode", allchans, autojoin=True)
elif use_mode == "testing":
    log.info("\x0304Testing mode enabled!\x03")
    channels = engine.execute(select([dbc.c.channel]).where(
        dbc.c.mode == "testing"
    )).fetchall()
    chans = []
    for channel in channels:
        chans.append(channel[0])
    ourchans = set(chans)
    quote.extra_channels["ecode"] |= ourchans
    allchans = quote.extra_channels["ecode"]
    quote.join("ecode", allchans, autojoin=True)

##
#
#  End Join Channels
#
####
#
#  Main / Die
#
##
def main(irc=None):
    permissions.addDefaultPermissions(default_permissions)
def die(irc):
    permissions.removeDefaultPermissions(default_permissions)
    utils.unregisterService("quote")
##
#
#  End Main / Die
#
####
#
#  Commands / Command-Like Functions
#
##



def rquote(irc, source, args):
    """takes no arguments
    Returns a random quote.
    """
    channel = irc.called_in
    if irc.called_in == source:
        error(irc, "This command must be done in a channel")
    else:
        ids = engine.execute(select([dbq.c.id]).where(
            dbq.c.channel == channel
        )).fetchall()
        if ids == []:
            error(irc, "No quotes exist for this channel")
        else:
            id_list = [x[0] for x in ids]
            random_id = random.choice(id_list)
            result = engine.execute(select([dbq]).where(and_(
                dbq.c.id == "%s" % random_id,
                dbq.c.channel == channel
            ))).fetchone()
            row_dict = dict(result.items())
            reply(irc, format(row_dict, chan=False))
quote.add_cmd(rquote, "quote")

q_parser = utils.IRCParser()
q_parser.add_argument("-i", "--id", action="store_true", default=True)
q_parser.add_argument("-w", "--wildcard", action="store_true")
q_parser.add_argument("-b", "--by", action="store_true")
q_parser.add_argument("query")
def q(irc, source, args):
    """<[options]> <query>
    Looks up a quote in the database for the current channel.

    In addition to just running the command with a quote ID,
    you are able to use the following switch arguments.


    -i/--id: Look up a quote by quote ID. (default)

    -w/--wildcard: Look up quotes by quote text searching.

    -b/--by: Look up quotes by the submitter's hostmask
    """
    channel = irc.called_in
    options = q_parser.parse_args(args)

    if irc.called_in == source:
        error(irc, "quotes must be grabbed using a channel, not a 1to1 message.")

    if options.id and not options.wildcard and not options.by:
        try:
            id = int(options.query)
            s = select([dbq]).where(and_(
                dbq.c.id == id,
                dbq.c.channel == irc.called_in
            ))
            result = engine.execute(s).fetchone()
            if result == None:
                error(irc, "No quote under that id.")
            else:
                reply(irc, format(dict(result.items()), chan=False))            
        except ValueError:
            error(irc, "ID must be a integer.")

    elif options.wildcard:
        regex = options.query
        s = select([dbq.c.id]).where(and_(
            dbq.c.quote.like("%{}%".format(regex)),
            dbq.c.channel == irc.called_in
        ))
        result = engine.execute(s).fetchall()
        qlist = [x[0] for x in result]
        if qlist == []:
            error(irc, "No quotes available for that wildcard search")
        else:
            reply(irc, "Quotes: %s" % squishids(qlist))
    elif options.by:
        by = options.query
        s = select([dbq.c.id]).where(and_(
            dbq.c.added_by == by,
            dbq.c.channel == irc.called_in
        ))
        result = engine.execute(s).fetchall()
        qlist = [x[0] for x in result]
        if qlist == []:
            error(irc, "No quotes were added by this person.")
        else:
            reply(irc, "Quotes: %s" % squishids(qlist))
        
quote.add_cmd(q, "q")

qadd_parser = utils.IRCParser()
qadd_parser.add_argument("quote", nargs='+')
def qadd(irc, source, args):
    """<quote text>
    Adds a quote to the bots database."""
    options = qadd_parser.parse_args(args)
    ourquote = " ".join(options.quote)
    if irc.called_in == source:
        if irc.checkAuthenticated(source, allowAuthed=True):
            reply("Please see 'addquote' for arbitrary adding.", notice=True, private=True)
        else:
            error(irc, "quotes must be sent in using a channel, not a 1to1 message.")
    s = select([dbcd.c.next_id]).where(dbcd.c.channel == irc.called_in)
    try:
        result = engine.execute(s).fetchone()[0]
    except exc.OperationalError as e:
        log.error("OperationalError Occured:")
        log.error("Exception Details: %s" % e)
        error(irc, "Stale Database Connection, Please try again.")
        error(irc, "If you've already tried once or twice, please forward this error to an admin, who may, or may not already know.")
        return
    
    next_id = result
    channel = irc.called_in
    ins = dbq.insert().values(
        id=next_id,
        channel=irc.called_in,
        quote=ourquote,
        added_by=irc.getHostmask(source)
    )
    try:
        engine.execute(ins)
    except exc.OperationalError as e:
        log.error("OperationalError Occured:")
        log.error("Exception Details: %s" % e)
        error(irc, "Stale Database Connection, Please try again.")
    reply(irc, "Done. Quote #%s added." % next_id)
    new_nextid = int(next_id) + 1
    updated = engine.execute(dbcd.update().where(
        dbcd.c.channel == channel
    ).values(next_id=new_nextid))
quote.add_cmd(qadd, "qadd")

qdel_parser = utils.IRCParser()
qdel_parser.add_argument("id")
def qdel(irc, source, args):
    """<id>
    Deletes quote #<id> from the database.
    """
    try:
        permissions.checkPermissions(irc, source, ["quotes.admin"])
    except utils.NotAuthorizedError:
        if irc.channels[irc.called_in].isOpPlus(source):
            pass
        else:
            error(irc, "Access denied. You must be a channel op to remove quotes.")
            return
    options = qdel_parser.parse_args(args)
    channel = irc.called_in
    id = options.id
    try:
        result = engine.execute(dbq.delete().where(and_(
            dbq.c.id      == id,
            dbq.c.channel == channel
        ))).rowcount
    except exc.OperationalError as e:
        log.error("OperationalError Occured:")
        log.error("Exception Details: %s" % e)
        error(irc, "Stale Database Connection, Please try again.")
    if result:
        reply(irc, "Done. Quote #%s deleted." % (id))
    else:
        error(irc, "Error occured when deleting quote. Please contact my Admins (Network Staff) for assistance.")
quote.add_cmd(qdel, "qdel")

##
#
#  End User Commands
#
####
#
#  Admin Commands
#
##

def stats(irc, source, args):
    """takes no arguments
    Returns stats on the quotes and channels in the database.
    """
    permissions.checkPermissions(irc, source, ["quotes.admin"])
    statdict = {}
    try:
        statdict["total_quote_count"] = engine.execute(
            dbq.count()
        ).fetchall()[0][0]
        statdict["total_channel_count"] = engine.execute(
            dbc.count()
        ).fetchall()[0][0]
    except exc.OperationalError as e:
        log.error("OperationalError Occured:")
        log.error("Exception Details: %s" % e)
        error(irc, "Stale Database Connection, Please try again.")
    reply(irc, "Quotes: %(total_quote_count)s / Channels: %(total_channel_count)s" % (statdict))
quote.add_cmd(stats, "stats")

addq_parser = utils.IRCParser()
addq_parser.add_argument("channel", type=str)
addq_parser.add_argument("quote", type=str, nargs='?')
def addquote(irc, source, args):
    """<channel> <quote text>
    Adds a quote to the database for the given channel."""
    permissions.checkPermissions(irc, source, ["quotes.admin"])

    options = addq_parser.parse_args(args)
    quote = " ".join(options.quote)
    s = select([dbcd.c.next_id]).where(
        dbcd.c.channel == options.channel
    )
    try:
        result = engine.execute(s).fetchone()[0]
    except exc.OperationalError as e:
        log.error("OperationalError Occured:")
        log.error("Exception Details: %s" % e)
        error(irc, "Stale Database Connection, Please try again.")
    next_id = result
    channel = options.channel

    ins = dbq.insert().values(
        id=next_id,
        channel=options.channel,
        quote=quote,
        added_by="addquote!addquote@addquote")
    engine.execute(ins)
    nnextid = int(next_id) + 1
    updateme = engine.execute(dbcd.update().where(
        dbcd.c.channel == options.channel
    ).values(next_id=nnextid)).rowcount

quote.add_cmd(addquote, "addquote")

getq_parser = utils.IRCParser()
getq_parser.add_argument("channel", type=str)
getq_parser.add_argument("-i", "--id", action="store_true", default=True)
getq_parser.add_argument("-w", "--wildcard", action="store_true")
getq_parser.add_argument("-b", "--by", action="store_true")
getq_parser.add_argument("query")

def getquote(irc, source, args):
    """<channel> <[options]> <query>
    Looks up a quote in the database for the given channel.

    In addition to just running the command with a quote ID,
    you are able to use the following switch arguments.


    -i/--id:
    Look up a quote by quote ID. (default)

    -w/--wildcard:
    Look up quotes by quote text searching.

    -b/--by:
    Look up quotes by the submitter's hostmask
    """
    permissions.checkPermissions(irc, source, ["quotes.admin"])
    options = getq_parser.parse_args(args)
    channel = options.channel
    if options.id and not options.wildcard and not options.by:
        try:                
            id = int(options.query)
            s = select([dbq]).where(and_(
                dbq.c.id == id,
                dbq.c.channel == options.channel,
            ))
            try:
                result = engine.execute(s).fetchone()
            except exc.OperationalError as e:
                log.error("OperationalError Occured:")
                log.error("Exception Details: %s" % e)
                error(irc, "Stale Database Connection, Please try again.")
            if result == None:
                error(irc, "No quote under that id.")
            else:
                reply(irc, format(dict(result.items()), chan=True))
        except ValueError:
            error(irc, "ID must be an integer!")
    elif options.wildcard:
        regex = options.query
        s = select([dbq.c.id]).where(and_(
                dbq.c.quote.like("%{}%".format(options.query)),
                dbq.c.channel == options.channel
        ))
        try:
            result = engine.execute(s).fetchall()
        except exc.OperationalError as e:
            log.error("OperationalError Occured:")
            log.error("Exception Details: %s" % e)
            error(irc, "Stale Database Connection, Please try again.")
        qlist = [x[0] for x in result]
        if qlist == []:
            error(irc, "No quotes available.")
        else:
            reply(irc, "Quote IDs: {}".format(squishids(qlist)))
    elif options.by:
        by = options.query
        s = dbq.select().where(and_(
            dbq.c.added_by == by,
            dbq.c.channel == options.channel
        ))
quote.add_cmd(getquote, "getquote")

getqs_parser = utils.IRCParser()
getqs_parser.add_argument("channel", type=str)
def getquotes(irc, source, args):
    """<channel>
    Get the list of quotes for a certain channel.
    """
    permissions.checkPermissions(irc, source, ["quotes.admin"])
    options = getqs_parser.parse_args(args)
    s = select([dbq.c.id]).where(dbq.c.channel == options.channel)
    try:
        result = engine.execute(s)
    except exc.OperationalError as e:
        log.error("OperationalError Occured:")
        log.error("Exception Details: %s" % e)
        error(irc, "Stale Database Connection, Please try again.")
    qlist = [x[0] for x in result]
    if qlist == []:
        reply(irc, "No quotes exist for that channel.")
    else:
        reply(irc, squishids(qlist))
quote.add_cmd(getquotes, "getquotes")

delq_parser = utils.IRCParser()
delq_parser.add_argument("channel", type=str)
delq_parser.add_argument("id", type=int)
def delquote(irc, source, args):
    """<channel> <id>
    Deletes the given <id> from the database for <channel>
    """
    permissions.checkPermissions(irc, source, ["quotes.admin"])
    options = delq_parser.parse_args(args)
    channel = options.channel
    id = options.id
    s = dbq.delete().where(and_(
            dbq.c.id      == id,
            dbq.c.channel == channel,
        )
    )
    try:
        result = engine.execute(s).rowcount
    except exc.OperationalError as e:
        log.error("OperationalError Occured:")
        log.error("Exception Details: %s" % e)
        error(irc, "Stale Database Connection, Please try again.")
    if result:
        reply(irc, "Done. Quote #%s deleted." % (id))
    else:
        error(irc, "No quote under that id.")
quote.add_cmd(delquote, "delquote")

def hook_invite(irc, source, command, args):
    channel = args["channel"]
    nick = irc.getFriendlyName(source)
    target = irc.getFriendlyName(args["target"])
    # target is ourselves so don"t worry about that.
    
    if target == "Quote":
        channel_id = ""
        s = dbcd.select().where(
            dbcd.c.channel == channel
        )
        try:
            chandata = engine.execute(s).fetchone()
        except exc.OperationalError as e:
            log.error("OperationalError Occured:")
            log.error("Exception Details: %s" % e)
            error(irc, "Stale Database Connection, Please try again.")
            error(irc, "If you've already done this more than once, let an admin know.")
        channel_row = None
        if chandata:
            channel_row = engine.execute(dbc.select().where(and_(
                dbc.c.channel == channel,
                dbc.c.id      == chandata[0]
            ))).fetchone()
        
            log.info("Channel Data exists for %s, using previous id" % channel)
            channel_id = chandata[0]
        else:
            log.info("%s is a new channel, initializing channel data." % channel)
            newchannel = engine.execute(dbcd.insert().values(
                    channel=channel,
                    next_id=1
            )).rowcount
            channel_id = engine.execute(select([dbcd.c.cid]).where(
                dbcd.c.channel == channel
            )).fetchone()
        if channel_row:
            irc.msg(source, "I'm already on %s" % channel, notice=True, source=quote.uids.get(irc.name))
        else:
            log.info("Got invite to %s from %s(%s) for %s" % (channel, nick, irc.getHostmask(source), target))
            log.info("Joining %s" % channel)
            quote.join(irc, "%s" % channel)
            if channel_row:
                pass
            else:
                ins = dbc.insert().values(
                    id=channel_id,
                    channel=channel,
                    added_by=irc.getHostmask(source),
                    private=options.private,
                    mode=options.mode,
                    invited=0
                )
                result = engine.execute(ins).rowcount
                if result > 0:
                    log.info("Joined %s due to invite." % channel)
utils.add_hook(hook_invite, "INVITE")

##
#
#  End Admin Commands
#
####
#
#  Maintenance Commands
#
##
join_parser = utils.IRCParser()
join_parser.add_argument("channel", type=str)
join_parser.add_argument("-p", "--private", default=0, choices=[0, 1])
join_parser.add_argument("-m", "--mode", default="production", type=str, choices=["production", "testing"])
def join(irc, source, args):
    """<channel> <[options]>
    Joins a channel with the given options,
    
    -p/--private
    
        —Marks the channel as private
        
    
    
    -m/--mode
    
        —Marks the channel for use in a certain mode
        
        
        This would be use to add a channel for development purposes,
        
        or to add channels to production mode while in testing mode. Etc.
        """
    permissions.checkPermissions(irc, source, ["quotes.admin"])

    options = join_parser.parse_args(args)
    if options.channel.startswith("#"):
        # if a channel_data row exists for the channel,
        # we know we have quotes from that channel
        channel_id = None
        try:
            chandata = engine.execute(select([dbcd.c.cid]).where(
                dbcd.c.channel == options.channel
            )).fetchone()
        except exc.OperationalError as e:
            log.error("Non-Critical Error: %s" % e)
            log.error("Stale Database Connection")
            error(irc, "Stale DB Connection, Please Try Again.")
        channel_row = None
        if chandata:
            channel_row = engine.execute(dbc.select().where(and_(
                dbc.c.channel == options.channel,
                dbc.c.id      == chandata[0]
            ))).fetchone()
            log.info("already have channel data on %s, using current existing channel id" % options.channel)
            channel_id = chandata[0]
        else:
            log.info("%s is a new channel, creating new channel data." % options.channel)
            newchannel = engine.execute(dbcd.insert().values(
                channel=options.channel,
                next_id=1
            )).rowcount
            channel_id = engine.execute(select([dbcd.c.cid]).where(
                dbcd.c.channel == options.channel
            )).fetchone()[0]
        if channel_row:
            log.debug("We already have a channel row for {}".format(options.channel))
            log.info("Already in {}".format(options.channel))
            error(irc, "I'm already in that channel!")
        else:
            log.info("Joining {}".format(options.channel))
            quote.join(irc, "%s" % options.channel)
            ins = engine.execute(dbc.insert().values(
                id=channel_id,
                channel=options.channel,
                added_by=irc.getHostmask(source),
                private=options.private,
                mode=options.mode,
                invited="0"
            )).rowcount
            result = engine.execute(select([dbc.c.id, dbc.c.added]
                ).where(and_(
                    dbc.c.id == channel_id,
                    dbc.c.channel == options.channel
                ))).fetchall()
            if result:
                log.info("Added channel row to database. Channel: {} ID: {} Time: {}".format(options.channel, result[0][0], str(result[0][1])))
                reply(irc, "Joining {}".format(options.channel))
    else:
        error(irc, "Channel name must start with a '#'")
quote.add_cmd(join, "join")

part_parser = utils.IRCParser()
part_parser.add_argument("channel", type=str)
part_parser.add_argument("-r", "--reason", type=str, nargs='?')
def part(irc, source, args):
    """<channel> <[-r REASON]>
    Leaves the given channel, with an optional reason.
    
    
    This deletes the channel's row in the database, and persists throughout restarts, reloads, rehashes, etc."""
    permissions.checkPermissions(irc, source, ["quotes.admin"])
    options = part_parser.parse_args(args)
    if options.channel.startswith('#'):
        pass
    else:
        error(irc, "channel names start with a '#'")
        return
    part_reason = None
    if options.reason:
        part_reason = " ".join(options.reason)
        irc.proto.part(quote.uids.get(irc.name), options.channel, part_reason)
    else:
        irc.proto.part(quote.uids.get(irc.name), options.channel, "Requested.")
        
    delstmt = dbc.delete().where(
        dbc.c.channel == options.channel
    )
    try:
        result = engine.execute(delstmt).rowcount
    except exc.OperationError as e:
        log.error("Stale Database Connection")
        error(irc, "Stale Database Connection, please try again.")
    if result > 0:
        reply(irc, "Channel removed")
    else:
        reply(irc, "We've already left this channel, or haven't joined it in the first place")

quote.add_cmd(part, "part")

gni_parser = utils.IRCParser()
gni_parser.add_argument("channel", type=str)
def getnextid(irc, source, args):
    """<channel>
    Returns the next quote ID for use in <channel>"""
    permissions.checkPermissions(irc, source, ["quotes.admin"])
    options = gni_parser.parse_args(args)
    channel = options.channel
    if channel.startswith("#"):
        try:
            result = engine.execute(select([dbcd.c.next_id]).where(
                dbcd.c.channel == channel
            )).rowcount
        except exc.OperationalError as e:
            log.error("Stale Database Connection")
            error(irc, "Stale DB Connection, please try again.")
        if result > 0:
            next_id = engine.execute(select([dbcd.c.next_id]).where(
                dbcd.c.channel == channel
            )).fetchone()
            if next_id:
                reply(irc, "Next Quote ID for {0}: {1}".format(options.channel, next_id[0]))
            else:
                error(irc, "An error occured.")
        else:
            error(irc, "This channel doesn't have any channel data")
    else:
        error(irc, "channel must start with a '#'")
quote.add_cmd(getnextid, "getnextid")

sni_parser = utils.IRCParser()
sni_parser.add_argument("channel", type=str)
sni_parser.add_argument("int", type=int)
def setnextid(irc, source, args):
    """<channel> <ID>
    Sets the next quote ID in <channel> to <ID>.
    
    
    This command should only be used if quotes were deleted after a certain number, as overwriting quotes is not supported."""
    permissions.checkPermissions(irc, source, ["quotes.admin"])
    options = sni_parser.parse_args(args)
    if not options.int:
        log.error("Did not receive a ID to set.")
    else:
        ins = dbcd.update().where(
            dbcd.c.channel == options.channel
        ).values(
            next_id=options.int
        )
        try:
            engine.execute(ins).rowcount
        except exc.OperationalError as e:
            log.error("Stale DB Connection")
            error(irc, "Stale DB Connection, please try again.")
        if ins > 0:
            reply(irc, "Set {}'s next id to {}".format(options.channel, options.int))
        else:
            error(irc, "An error occured.")
quote.add_cmd(setnextid, "setnextid")

def g(irc, source, args):
    """<[message]>
    Sends a message to all channels the bot is in,
    as a global message, aka AMSG."""
    error(irc, "Not Implemented")
quote.add_cmd(g, "global")

##
#
#  End Maintenance Commands
#
####
#
#  Can haz CTCP?
#
##

plugin_source = {
    "framework": "Pylink(%s)" % pylinkirc.real_version,
    "plugin":    "This plugin is made by Iota/Ken, plugin history @ https://git.io/vDUTN / code @ https://git.io/vDUTh",
}
plugin_version = {
    "framework": "Pylink(%s)" % pylinkirc.real_version,
    "plugin":    "1.0"
}

def handle_source(irc, source, args):
    """
    Handles CTCP SOURCE requests
    """
    for k,v in plugin_source.items():
        irc.msg(source, "\x01SOURCE %s - %s\x01" % (k.capitalize(),v), notice=True)
def handle_version(irc, source, args):
    """
    Handles CTCP VERSION requests
    """
    for k,v in plugin_version.items():
        irc.msg(source, "\x01VERSION %s - %s\x01" % (k.capitalize(), v), notice=True)
quote.add_cmd(handle_version, "\x01VERSION\x01")
quote.add_cmd(handle_source, "\x01SOURCE\x01")

##
#
# End Commands / CTCP
#
##
