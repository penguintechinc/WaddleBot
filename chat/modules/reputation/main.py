#!/usr/bin/python3
from libs.botClasses import *
import pathlib
from updater import update
from libs.botLogger import BotLogger as botLogger
from query import query

# Const
CONFIG_FILE = f"{pathlib.Path(__file__).parent.resolve()}config.yml"


# Why is that black van out there?
log = botLogger("reputation-main")
#log.fileLogger("reputation.log")

# ---------------------
# This is the function which lambda will call
# ---------------------

def receiving(activity, userid, platform, interface, text: str = None, 
              namespace: str = "global", subinterface: str = None, amount: float = 0):
    # Initiate the logger
    # Why are we even here bruh?
    ee = event
    ee.activity = activity
    ee.amount = amount
    ee.platform = platform
    ee.interface = interface
    ee.subInterface = subinterface
    ee.namespace = namespace
    ee.rawText = text

    # Setup dat identity yo
    userid = identity
    userid.id = userid
    userid.platform = [platform]

    # Returning something variable phool
    msg = None
    media = None
    stdout = "dm"

    # Do we seek truth?
    if platform == "query":
        log.debug("Query platform detected")
        x = query(userid, CONFIG_FILE=CONFIG_FILE)
        msg = x.idLookup()
    else:
        match platform:
            case "twitch":
                log.debug("Twitch platform detected")
                x = update(userid, ee, CONFIG_FILE=CONFIG_FILE)
                x.twitch()
            case "discord":
                log.debug("Discord platform detected")
                x = update(userid, ee, CONFIG_FILE=CONFIG_FILE)
                x.discord()
            case "youtube":
                log.debug("Youtube platform detected")
                x = update(userid, ee, CONFIG_FILE=CONFIG_FILE)
                x.youtube()
            case _:
                log.error("I am not programmed to handle this platform")
    return msg, media, stdout
