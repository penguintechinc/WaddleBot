from libs.botClasses import *
from libs.botDBC import botDb as dbc
from libs.botConfig import botConfig as bc
from libs.botLogger import botLogger

# Why is that black van out there?
log = botLogger("reputation-query")
log.fileLogger("reputation.log")

# ---------------------
# This is the function which will query current rep and rep modifiers
# ---------------------

class query:
    def __init__(self, userid: identity, CONFIG_FILE) -> None:
        self.score = 0
        self.id = userid
        self.retvars = retvars
        self.config = bc(configPath=CONFIG_FILE)
        self.dbc = dbc(config=self.config)
        log.debug(f"Query object initiated for {self.id.id}")
    # ---------------------
    # Lookup an ID's reputation
    # ---------------------
    
    def idRep(self):
        lookCol = "userid"
        database = "waddlebot"
        table = "reputation"
        scoreDBQ = dbquery
        scoreDBQ.columns = "score"
        scoreDBQ.queryColumn = lookCol
        scoreDBQ.queryValue = self.id.id
        scoreDBQ.database = database
        scoreDBQ.table = table
        x = dbc
        y = x.webdbRead(query = scoreDBQ)
        self.score = y[0][0]
        log.debug(f"Score for {self.id.id} is {self.score}")
        return self.score
    
    # ---------------------
    # Return the alias name for the current score
    # ---------------------
    
    def repAlias(self, score: float = 600):
        for alias, range in self.config["reputation-alias"]:
            if score > range[0] and score < range[1]:
                log.debug(f"Alias for {score} is {alias}")
                return alias
        log.error(f"No alias found for {score}")
        return "no alias found!"
