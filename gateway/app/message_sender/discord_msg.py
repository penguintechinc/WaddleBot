import requests
from requests.exceptions import RequestException, HTTPError, ConnectionError, Timeout
from retrying import retry
from WaddlebotLibs.botLogger import BotLogger

# CONSTANTS
LOG_LEVEL = "INFO"

# Initiate the logger
log = BotLogger(logFile="gateway_creator.log")
log.fileLogger()

class Discord_Message_Sender:
    def __init__(self, token, server_id, message):
        self.token = token
        self.server_id = server_id
        self.message = message

        self.user_id = self.get_owner_id(server_id)
        self.channel_id = self.create_dm_channel()

    def send_message(self):
        log.info(f"Sending message to channel {self.channel_id}")

        url = f'https://discord.com/api/v10/channels/{self.channel_id}/messages'
        data = {"content": self.message}
        header = {"Authorization": f"Bot {self.token}"}

        r = requests.post(url, data=data, headers=header)
        
        log.info(f"Status code: {r.status_code}")

    def create_dm_channel(self):
        if self.user_id is None:
            log.error("User id not found")
            return None
        
        log.info(f"Creating DM channel with user {self.user_id}")

        data = {"recipient_id": self.user_id}
        headers = {"Authorization": f"Bot {self.token}"}

        r = requests.post(f'https://discord.com/api/v10/users/@me/channels', json=data, headers=headers)

        log.info(f"Status code: {r.status_code}")

        channel_id = r.json()['id']

        return channel_id
    
    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def get_owner_id(self, server_name):
        log.info(f"Getting owner id of server {server_name}")

        url = f'https://discord.com/api/v10/guilds/{server_name}'
        headers = {"Authorization": f"Bot {self.token}"}
        
        try:
            r = requests.get(url, headers=headers)
            r.raise_for_status()
        except (HTTPError, ConnectionError, Timeout) as e:
            log.error(f"Request failed: {e}")
            raise
        except RequestException as e:
            log.error(f"An error occurred: {e}")
            raise

        if r.status_code == 200:
            log.info(f"Server {server_name} found. Getting owner.")

            data = r.json()
            # The key 'owner_id' is the owner of the server. Check if this key is in the data
            if 'owner_id' in data:
                return data['owner_id']
        else:
            log.error(f"Server {server_name} not found. Status code: {r.status_code}")
            return None