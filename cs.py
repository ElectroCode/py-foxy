# cs.py: some chanserv based things
from pylinkirc import utils, world
from pylinkirc.log import log

desc = "Welcome bot. Messages newly registered channels with helpful info."

welcome = utils.registerService("welcome", nick="Welcome", ident="Welcome", desc=desc)

def hook_privmsg(irc, source, command, args):
    weuid = irc.nickToUid('Welcome')
    
    channel = args['target']
    text = args['text']

    # irc.pseudoclient stores the IrcUser object of the main PyLink client.
    # (i.e. the user defined in the bot: section of the config)
    if 'used REGISTER on' in text and channel == '#debug':
        nick = text.split()
        nick = nick[1]
        nick = nick.split('!')
        nick = nick[0]
        
        regchannel = text.split()
        regchannel = regchannel[6]
        irc.proto.join(weuid, regchannel)
        irc.proto.message(weuid, regchannel, 'Welcome to ElectroCode, %s' % nick)
        irc.proto.message(weuid, regchannel, "I've auto-assigned a bot for you to use. If you want a different one, you can look at '/bs botlist'.")
        irc.proto.message(weuid, regchannel, "If you have any problems, please join '#help'.")
        irc.proto.message(weuid, regchannel, "If you've seen this before, just ignore me.")
        irc.proto.part(weuid, regchannel, "Welcome")
utils.add_hook(hook_privmsg, 'PRIVMSG')

def die(irc):
    utils.unregisterService('welcome')