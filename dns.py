# dns.py: DNS for network
# -*- coding: utf-8 -*-
import pylinkirc
from pylinkirc import utils, world, conf
from pylinkirc.coremods import permissions
from pylinkirc.log import log

import CloudFlare
import json

cf_conf = conf.conf.get("cf", {})
def get_cf():
    
    email = cf_conf.get("cf-email", "")
    key =   cf_conf.get("cf-key", "")
    
    return CloudFlare.CloudFlare(email=email, token=key, raw=True)

def cf_add(options):
    cf = get_cf()

    body = {
        "type":    options.type,
        "name":    options.name,
        "content": options.content,
    }
    body["ttl"] = options.ttl if options.ttl else 1

    return cf.zones.dns_records.post(options.zone, data = body)
    

def cf_show(options):
    cf = get_cf()

    body = {
        "order": options.order,
        "type":  options.type
    }

    if options.name:
        body["name"]    = options.name
    if options.content:
        body["content"] = options.content

    return cf.zones.dns_records.get(options.zone, params = body)

def cf_rem(options):
    cf = get_cf()

    return cf.zones.dns_records.delete(options.zone, options.id)

##
#
# Arg Parsing
#
##
parser = utils.IRCParser()
parser.set_defaults(zone=cf_conf.get("cf-zone", ""))
subparsers = parser.add_subparsers()

rr_add = subparsers.add_parser("add")
rr_add.set_defaults(command="cf_add")
rr_show = subparsers.add_parser("show")
rr_show.set_defaults(command="cf_show")
rr_rem = subparsers.add_parser("rem")
rr_rem.set_defaults(command="cf_rem")

##
#
# Commands
#
##

rr_add.add_argument("name")
rr_add.add_argument("content")
rr_add.add_argument("-t", "--type", choices=["A", "AAAA", "CNAME"], required=True)
rr_add.add_argument("-l", "--ttl", type=int)

rr_show.add_argument("-t", "--type", choices=["A", "AAAA", "CNAME"])
rr_show.add_argument("-n", "--name")
rr_show.add_argument("-c", "--content")
rr_show.add_argument("-o", "--order", default="type")


rr_rem.add_argument("id")
def rr(irc, source, args):
    """{ADD|SHOW|DEL} <arguments>


    ————

    \x02ADD\x02:


    —    Syntax: \x02NAME\x02 \x02CONTENT\x02 \x02OPTIONS...\x02


    —        -t / --type : Type of Record

    —            Choices: A, AAAA, CNAME


    —        -l / --ttl : TTL of record (Time to live)

    —            If not given, ttl is made automatic

    —    Adds a record to a RR group of records


    \x02SHOW\x02:


    —    Syntax: [\x02SUBDOMAIN\x02]


    —        -n / --name : Name / Subdomain

    —        -t / --type : Type of record

    —        -c / --content : Content of record / IP

    —        -o / --order : Order by ...

    —            type, content, name


    —    Search records


    \x02REM\x02:


    —    Syntax: \x02RECORD ID\x02

    —        This command takes no other arguments.


    —    Removes a record.


    ————
    """
    options = ""
    permissions.checkPermissions(irc, source, ['dns.rr'])
    if args:
        options = parser.parse_args(args)
    else:
        irc.reply("Syntax: rr {ADD|SHOW|DEL} <args...>")
        irc.reply("See 'help rr' for more info.")
    if options.command == "cf_add":
        response = cf_add(options)
        if response:
            result = response["result"]
            irc.reply("Record Added. %(name)s as %(content)s" % result, private=False)
            irc.reply("Record ID: %(id)s" % result, private=False)

    elif options.command == "cf_show":
        response = cf_show(options)
        count = response.get("result_info", {}).get("count", 0)
        result = response.get("result", [])
        irc.reply("Found %d records" % count, private=False)
        for res in result:
            irc.reply("\x02Name\x02: %(name)s \x02Content\x02: %(content)s" % res, private=False)
            irc.reply("\x02ID\x02: %(id)s" % res, private=False)

    elif options.command == "cf_rem":
        response = cf_rem(options)
        result = response["result"]
        irc.reply("Record Removed. ID: %(id)s" % result, private=False)
    
utils.add_cmd(rr, "rr", featured=True)
