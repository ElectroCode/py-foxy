## py-foxy Plugins

* py-foxy Plugins is a repo housing plugins for pylinkirc,
    originally used only on ElectroCode, but can be used 
    on any network.

### Service Bot Configuration

* Any service bots that are included with a plugin can have their `nick`
    and `ident` changed by creating a new section at the bottom of your
    *.yml file that you use to start the pylink instance.
  
  
  * connversion.py
    * Section: `ctcp`

  * quotes.py
    * Section: `quote`
    
    * Extra Directives:
      * `db`: sqlalchemy url to your quote database.
        * ''Note'': Please add 'channels', 'channel_data', and 'quotes' as
          tables in the database before using. 
      * `mode`: if you plan using this plugin, add this directive and set it to production

  * cs.py
    * Section: `welcome` 


#### connversion.py

* runs a `CTCP VERSION` on users on connect.

  * Note: For each server this links to,
    you must put the SIDs into each server block.
    `irc.serverdata.get('sids', [])` uses this to make sure its not
    `VERSION`ing over the relay if you have it loaded.
  * Currently only supported on InspIRCd, due to checking connect notice,
    if you would like another IRCd supported, please contact me with an example
    from that IRCd. 



##### Plugin Configuration


  * For those using plugins without service bots, there may still be
      some configuration.

    * dns.py
      * Section: `cf`

      * Extra Directives: all prefixed with 'cf-'

        * `email`: Cloudflare Account Email
        * `key`: Cloudflare Account token/key
        * `zone`: The zone ID you're going to be using.

    * dnsbl.py
      * Section: `dnsbl`

      * Extra Directives: