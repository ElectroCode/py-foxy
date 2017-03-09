# foxy.py: some fun stuff for the foxy
from pylinkirc import utils
from pylinkirc.log import log

import random

def pet(irc, source, args):
    if irc.pseudoclient.nick == "py-foxy":
        # if <= 25, purrs
        # if 26-49, whines
        # if 50-74, scratches
        # if 75-100, kills
        result = random.randrange(1,100)
        mynick = irc.pseudoclient.nick
        myuid = irc.nickToUid(mynick)
        if result in range(0,25):
            irc.reply('\x01ACTION purrs\x01')
        elif result in range(26,50):
            irc.reply('\x01ACTION whines\x01')
        elif result in range(51,75):
            irc.reply('\x01ACTION scratches %s\x01' % (irc.getFriendlyName(source)))
        elif result in range(76,100):
            irc.proto.kill(myuid, source, '* kills %s' % (irc.getFriendlyName(source)))

utils.add_cmd(pet, "pet")