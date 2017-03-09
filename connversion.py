# connversion.py: version users on connect
from pylinkirc import utils, world, conf
from pylinkirc.log import log

import time
desc = "CTCP bot, versions connecting users."

ctcp = utils.registerService("ctcp", desc=desc)

reply = ctcp.reply
error = ctcp.error


def hook_connversion(irc, source, command, args):
    oursids = irc.serverdata.get('sids', [])
    nickuid = source
    nicksid = irc.getServer(nickuid)
    nickts = int(irc.users[nickuid].ts)
    nowts = int(time.time())
    result = args['text']
    result = result.split()
    result = result[1:]
    result = (" ").join(result)
    result = result.strip('\x01')
    if nowts <= nickts + 15:
        if nicksid in oursids:
            myuid = ctcp.uids.get(irc.name)
            if args['text'].startswith('\x01') and args['text'].endswith('\x01'):
                irc.proto.message(myuid, '#debug', "Received VERSION reply from %s, using: %s" % (irc.getFriendlyName(source), result))

utils.add_hook(hook_connversion, 'NOTICE')

def hook_uid(irc, source, command, args):
    try:
        myuid = ctcp.uids.get(irc.name)
        oursids = irc.serverdata.get('sids', [])
        nick = args['nick']
        nickuid = args['uid']
        nowts = int(time.time())
        theirts = int(args['ts'])

        if source in oursids:
            irc.proto.message(myuid, nickuid, "\x01VERSION\x01")
    except LookupError:
        pass

utils.add_hook(hook_uid, 'UID')

def die(irc):
    utils.unregisterService('ctcp')