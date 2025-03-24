from libs.botClasses import *
import re
from libs.botDBC import botDb as db
from libs.botConfig import botConfig as cfg
from libs.botLogger import botLogger
from query import dbquery as dbq


# Why is that black van out there?
log = botLogger("reputation-updater")
log.fileLogger("reputation.log")

# ---------------------
# This is the function which will update the reputation of an identity
# ---------------------

class update:
    def __init__(self, id: identity, events: event, dbc: dbinfo, 
                 CONFIG_FILE: str) -> None:
        self.score = 0
        self.id = id
        self.event = events
        self.retvars = retvars
        self.config = cfg(configPath=CONFIG_FILE)
        self.dbc = db(configfile=self.config)
        log.debug(f"Update object initiated for {self.id.id}")

    # ---------------------
    # Take the event and adjust the score based on the event for Twitch
    # ---------------------
    
    def twitch(self):
        dbScore = dbquery
        dbScore.columns = ["score"]
        dbScore.queryColumn = "event"
        match self.event.activity:
            case re.match(r"(re-)?subscription, self.event.activity"):
                amount = 1
                if re.match(r"^tier 1"):
                    amount = 5
                if re.match(r"^tier 2"):
                    amount = 10
                if re.match(r"^tier 3"):
                    amount = 20
                scoreChange = self.__scoreAdjust(eventType="subscription", 
                                                 eventAmount=amount)
            case _:
                scoreChange = self.__scoreAdjust(eventType=self.event.activity)
        return self.__updateScores(scoreChange)
    
    # ---------------------
    # Take the event and adjust the score based on the event for Discord
    # ---------------------
    
    def discord(self):
        eventType = ""
        amount = 1.0
        match self.event.activity:
            case re.match(r"^(re-)?subscription, self.event.activity"):
                eventType = "supporter"
            case "join":
                eventType = "follower"
            case "boost":
                eventType = "supporter"
                amount = 3.5
            case "raffle":
                eventType = "raffle"
            case "giveaway":
                eventType = "giveaway"
            case "donation":
                eventType = "donation"
                amount = self.event.amount
        scoreChange = self.__scoreAdjust(eventType=eventType, eventAmount=amount)
        return self.__updateScores(scoreChange)

    '''
    # ---------------------
    # Take the event and adjust the score based on the event for Youtube
    # ---------------------
    def youtube(self):
        match self.event.activity:
            case re.match(r"^(re-)?subscription, self.event.activity"):
                pass
            case "join":
                pass
            case "super-text":
                pass
            case "raffle":
                pass
            case "giveaway":
                pass
            case "donation":
                pass
    
    # ---------------------
    # Take the event and adjust the score based on the event for Slack
    # ---------------------
    def slack(self):
        match self.event.activity:
            case re.match(r"^(re-)?subscription, self.event.activity"):
                pass
            case "join":
                pass
            case "raffle":
                pass
            case "giveaway":
                pass
            case "donation":
                pass
    
    # ---------------------
    # Take the event and adjust the score based on the event for Mattermost
    # ---------------------
    def mattermost(self):
        match self.event.activity:
            case re.match(r"^(re-)?subscription, self.event.activity"):
                pass
            case "join":
                pass
            case "raffle":
                pass
            case "giveaway":
                pass
            case "donation":
                pass
    # ---------------------
    # Check what the adjustment based on general type should be
    # ---------------------
    def __scoreAdjust(self, eventType: str, eventAmount: float = 1.0):
        scoreDBQ = dbquery
        scoreDBQ.columns = "adjustment"
        scoreDBQ.queryColumn = "event"
        scoreDBQ.queryValue = eventType
        y = self.dbc.webdbRead(query=scoreDBQ)
        log.debug(f"Adjustment for {eventType} is {y[0][0]}")
        return y[0][0] * eventAmount
    
    # ---------------------
    # Update the score in the database
    # ---------------------
    def __updateScore(self, score: float):
        scoreDBQ = dbquery
        scoreDBQ.columns = "score"
        scoreDBQ.queryColumn = "userid"
        scoreDBQ.queryValue = self.id.id
        y = self.dbc.webdbUpdate(query=scoreDBQ)
        log.debug(f"Score for {self.id.id} updated to {score}")
        return y
    '''
