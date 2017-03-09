# dnsbl.py: dnsbl checker 
# -*- coding: utf-8 -*-
import pylinkirc
from pylinkirc import utils, world, conf
from pylinkirc.coremods import permissions
from pylinkirc.log import log

from collections import OrderedDict
import dns.exception as exception
import dns.resolver as dns
import yaml
import yamlordereddictloader


import os

default_permissions = {
    "$ircop:*network admin*": ['dnsbl.*'],
    "$ircop": ['dnsbl.check', 'dnsbl.listrec', 'dnsbl.listbls']
}

class DNSBLError(Exception):
    pass

class Blacklists:
    def __init__(self):
        self.path = conf.conf.get('dnsbl', {}).get('path', 'blacklists.yml')
        
    def path(self):
        return self.path
    def _dict(self):
        return yaml.load(open(self.path, 'r'), Loader=yamlordereddictloader.Loader)
    
    def dump(self, updated_dict):
        yaml.dump(updated_dict, open(self.path, 'w'), default_flow_style=False)

dnsbl_addrec = utils.IRCParser()
dnsbl_addrec.add_argument('blacklist')
dnsbl_addrec.add_argument('record', type=int)
dnsbl_addrec.add_argument('reply', nargs=utils.IRCParser.REMAINDER)
def addrec(irc, source, args):
    """<blacklist> <record> <reply...>
    Adds a record reply for the given blacklist.
    """
    permissions.checkPermissions(irc, source, ["dnsbl.radd"])
    args = dnsbl_addrec.parse_args(args)
    bls = Blacklists()
    config = bls._dict()
    if config.get("blacklists", {}):
        blacklist = args.blacklist
        if config.get('blacklists').get(blacklist, {}):
            record = args.record
            reply = " ".join(args.reply)
            config['blacklists'][blacklist]['records'][record] = reply
            bls.dump(config)
            irc.reply("Record added to %s. %d: %s" % (blacklist, record, reply))
        else:
            irc.error("Blacklist %s is not defined" % blacklist)
    else:
        irc.error("Could not retrieve blacklists")

    
utils.add_cmd(addrec, "radd", featured=True)

dnsbl_remrec = utils.IRCParser()
dnsbl_remrec.add_argument('blacklist')
dnsbl_remrec.add_argument('record', type=int)
def remrec(irc, source, args):
    """<blacklist> <record>
    Removes record from blacklist.
    """
    permissions.checkPermissions(irc, source, ["dnsbl.rrem"])
    args = dnsbl_remrec.parse_args(args)
    bls = Blacklists()
    config = bls._dict()
    try:
        del config['blacklists'][args.blacklist]['records'][args.record]
        bls.dump(config)
        irc.reply("Record Reply removed.")
    except KeyError:
        irc.error("Reply did not exist.")
utils.add_cmd(remrec, "rrem", featured=True)

dnsbl_listrec = utils.IRCParser()
dnsbl_listrec.add_argument('blacklist')
def listrec(irc, source, args):
    """<blacklist>
    Lists all records for a blacklist
    """
    permissions.checkPermissions(irc, source, ["dnsbl.rlist"])    
    args = dnsbl_listrec.parse_args(args)
    bls = Blacklists()
    config = bls._dict()
    records = []
    try:
        for k, v in config['blacklists'][args.blacklist]['records'].items():
            records.append('%s - %s' % (k, v))
        msg_bls = 'Records: %s' % (' \xB7 '.join(records))
        irc.reply(msg_bls)
    except KeyError:
        if opts.blacklist:
            if config.get('blacklists').get(opts.blacklist):
                irc.reply("%s doesn't have a records section.")
utils.add_cmd(listrec, "rlist", featured=True)

dnsbl_listbls = utils.IRCParser()
def listbls(irc, source, args):
    """takes no arguments
    Lists all blacklists
    """
    permissions.checkPermissions(irc, source, ["dnsbl.bls"])    
    blacklists = Blacklists()
    bls = blacklists._dict()
    replies = []
    for bl, bd in bls['blacklists'].items():
        replies.append("%s — %s" % (bl, bd.get('hostname')))
    for reply in replies:
        irc.reply(reply)
utils.add_cmd(listbls, "bls", featured=True)

dnsbl_check = utils.IRCParser()
dnsbl_check.add_argument('ip')
dnsbl_check.add_argument('blacklist')
def blcheck(irc, source, args):
    """<ip> <[blacklist]>
    Checks if IP is in all blacklists defined, or in single
    blacklist given as second argument."""
    permissions.checkPermissions(irc, source, ["dnsbl.check"])
    args = dnsbl_check.parse_args(args)
    try: 
        irc.reply(ck(args.ip, args.blacklist))
    except DNSBLError as e:
        irc.error(e)
utils.add_cmd(blcheck, "check", featured=True)

dnsbl_addbl = utils.IRCParser()
dnsbl_addbl.add_argument('blacklist')
dnsbl_addbl.add_argument('hostname')
def addbl(irc, source, args):
    """<blacklist> <hostname>
    Adds BLACKLIST with hostname HOSTNAME.
    """
    permissions.checkPermissions(irc, source, ["dnsbl.add"])    
    args = dnsbl_addbl.parse_args(args)
    bls = Blacklists()
    config = bls._dict()
    try:
        config['blacklists'][args.blacklist] = {}
        config['blacklists'][args.blacklist]['hostname'] = args.hostname
        irc.reply("Blacklist %s added with hostname %s" % (args.blacklist, args.hostname))
        bls.dump(config)
    except KeyError as e:
        irc.error("Key %s does not exist. Ruh-roh" % e)
    
utils.add_cmd(addbl, "add", featured=True)

dnsbl_rembl = utils.IRCParser()
dnsbl_rembl.add_argument('blacklist')
def rembl(irc, source, args):
    """<blacklist>
    Removes BLACKLIST.
    """
    permissions.checkPermissions(irc, source, ["dnsbl.rem"])
    args = dnsbl_rembl.parse_args(args)
    bls = Blacklists()
    config = bls._dict()
    try:
        del config['blacklists'][args.blacklist]
        bls.dump(config)
        irc.reply("Blacklist removed.")
    except KeyError:
        irc.error("Supposed blacklist %s did/does not exist." % args.blacklist)
utils.add_cmd(rembl, "rem", featured=True)

def ck(host, bl=None):
    """Abstract method to run host through blacklists"""
    blacklists = Blacklists()
    bls = blacklists._dict()
    bls = bls['blacklists']
    ip = host.split('.')
    ip.reverse()
    ip = '.'.join(ip)    
    rdict = {'zones': [],
            'det': 0,
            'ndet': 0,
            'replies': {},                    
            }
    if bl:
        hostname = blacklists.get(bl, {}).get('hostname', "")
        if hostname == "":
            return {
                'failed': True,
                'error':   "An error occured getting hostname. Please review the following.",
                'desc': [
                    "Blacklist may not exist.",
                    "Blacklist may have no hostname set.",
            ]}
        rstring = ip+'.'+hostname
        try:
            for rdata in dns.query(rstring, 'A'):
                reply = str(rdata).split('.')[3]
                rdict['zones'] = bl
                rdict['replies'][name] = blacklists[name]['records'][reply]
        except exception.DNSException:
            return {
                'failed': True,
                'error': "Host not listed in blacklist.",
                }
    else:
        for name, blacklist in blacklists.items():
            rstring = ip+'.'+blacklist['hostname']
            try:
                for rdata in dns.query(rstring, 'A'):
                    if isinstance(rdata, 'list'):
                        return None
                    reply = str(rdata)
                    reply = reply.split('.')
                    reply = reply[3]
                    rdict['det'] += 1
                    rdict['zones'].append(name)
                    rdict['replies'][name] = blacklists[name]['records'][int(reply)]
            except exception.DNSException:
                rdict['ndet'] += 1
                
    return rdict
#def main(irc=None):
#    pass

#def die(irc=None):
#    pass