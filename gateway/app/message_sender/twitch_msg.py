# Config portion
import socket
# import pyttsx3
# import soundfx
from WaddlebotLibs.botLogger import BotLogger

# HOST = "irc.chat.twitch.tv"  # the twitch irc server
# PORT = 6667  # always use port 6667
# NICK = "fuzzybottgaming"  # twitch username, lowercase
# PASS = "oauth:[]"  # your twitch OAuth token
# CHAN = "#[my channel]"  # the channel you want to join

# CONSTANTS
LOG_LEVEL = "INFO"

# Initiate the logger
log = BotLogger(logFile="gateway_creator.log")
log.fileLogger()

class Twitch_Message_Sender:
    def __init__(self, HOST, PORT, NICK, PASS, CHAN):
        self.HOST = HOST
        self.PORT = PORT
        self.NICK = NICK
        self.PASS = PASS
        self.CHAN = CHAN

    def send_message(self, message):
        s = socket.socket()
        log.info("Connecting to twitch")
        log.info(f"HOST: {self.HOST}")
        log.info(f"PORT: {self.PORT}")
        s.connect((self.HOST, self.PORT))
        log.info("Connected to twitch")
        s.send(f"PASS {self.PASS}\r\n".encode("utf-8"))
        log.info("Sent pass")
        s.send(f"NICK {self.NICK}\r\n".encode("utf-8"))
        log.info("Sent nick")
        s.send(f"JOIN {self.CHAN}\r\n".encode("utf-8"))
        log.info("Sent join")
        s.send(f"PRIVMSG {self.CHAN} :{message}\r\n".encode("utf-8"))
        log.info("Sent message")
        s.send(f"PONG :tmi.twitch.tv\r\n".encode("utf-8"))
        log.info("Sent pong")
        s.close()
        log.info(f"Message sent to Twitch. Message: {message}")

        # If an error occurs, return a 500 error
        # if not s:
        #     log.info("Error sending message")
