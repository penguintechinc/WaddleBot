import requests
from flask import make_response, jsonify
from classes.gateway_classes import DiscordPayload
import traceback
import uuid
from urllib.parse import quote
import os
from dotenv import load_dotenv
from WaddlebotLibs.botLogger import BotLogger

# CONSTANTS
LOG_LEVEL = "INFO"

# Initiate the logger
log = BotLogger(logFile="gateway_creator.log")
log.fileLogger()

class GwHelpers:
    def __init__(self):
        # Load the environment variables
        load_dotenv()

        # Validate that the required environment variables are set
        self.validate_env_vars([
            'GATEWAY_CREATION_URL', 
            'GATEWAY_DELETION_URL', 
            'GATEWAY_SERVER_GET_URL', 
            'GATEWAY_SERVER_CREATE_URL', 
            'GATEWAY_SERVER_DELETE_URL', 
            'TWITCH_HOST',
            'TWITCH_PORT',
            'TWITCH_PASS',
            'TWITCH_NICK',
            'DISCORD_TOKEN',
            'DISCORD_BOT_INVITE_URL',
            'TWITCH_AUTH_URL',
            'TWITCH_AUTH_CLIENT_ID', 
            'TWITCH_AUTH_REDIRECT_URI',
            'TWITCH_AUTH_RESPONSE_TYPE',
            'TWITCH_AUTH_SCOPE'
        ])

        # Get the environment variables
        self.gateway_creation_url = os.getenv('GATEWAY_CREATION_URL')
        self.gateway_deletion_url = os.getenv('GATEWAY_DELETION_URL')
        self.gateway_server_get_url = os.getenv('GATEWAY_SERVER_GET_URL')
        self.gateway_server_create_url = os.getenv('GATEWAY_SERVER_CREATE_URL')
        self.gateway_server_delete_url = os.getenv('GATEWAY_SERVER_DELETE_URL')
        self.twitch_host = os.getenv('TWITCH_HOST')
        self.twitch_port = os.getenv('TWITCH_PORT')
        self.twitch_pass = os.getenv('TWITCH_PASS')
        self.twitch_nick = os.getenv('TWITCH_NICK')
        self.twitch_auth_url = os.getenv('TWITCH_AUTH_URL')
        self.twitch_auth_client_id = os.getenv('TWITCH_AUTH_CLIENT_ID')
        self.twitch_auth_redirect_uri = os.getenv('TWITCH_AUTH_REDIRECT_URI')
        self.twitch_auth_response_type = os.getenv('TWITCH_AUTH_RESPONSE_TYPE')
        self.twitch_auth_scope = os.getenv('TWITCH_AUTH_SCOPE')
        self.discord_token = os.getenv('DISCORD_TOKEN')
        self.discord_bot_invite_url = os.getenv('DISCORD_BOT_INVITE_URL')

    # Function to validate that all the given required environment variables are set
    def validate_env_vars(self, required_vars: list) -> None:
        """
        Validate that required environment variables are set
        Args:
            required_vars (list): List of required environment variable names
        Raises:
            Exception: If any required variable is not set
        """
        for var in required_vars:
            if var not in os.environ:
                log.error(f'{var} environment variable not set')
                raise Exception(f'{var} environment variable not set')

    def find_all_strings(self, text, startsub, endsub):
        results = []
        startidx = 0

        while startidx < len(text):
            startidx = text.find(startsub, startidx)
            if startidx == -1:  # startsub not found, stop searching
                break

            startidx += len(startsub)  # move the start index after the startsub

            endidx = text.find(endsub, startidx)
            if endidx == -1:  # endsub not found, stop searching
                break

            results.append(text[startidx:endidx])  # append the found string to results
            startidx = endidx + len(endsub)  # move the start index after the endsub for next search

        return results
    
    # Function to split a given command string into a list of strings. Each string command value is between [] brackets in the command string.
    def get_command_params(self, command_string: str) -> list:
        # Check if the command_string is given.
        return None if not command_string else self.find_all_strings(command_string, '[', ']')

    # Function to get the list of gateway servers from the gateway server service and return the list
    def get_gateway_servers(self, gateway_server_get_url) -> list:
        try:
            response = requests.get(gateway_server_get_url)
            response_payload = response.json()
            if 'data' not in response_payload and len(response_payload['data']) == 0:
                return make_response(jsonify({'msg': 'Something went wrong while getting the gateway servers. Please try again later, or contact a technician for further assistance'}), 500)

            response_data = response_payload['data']
            return response_data
        except Exception as e:
            log.error(traceback.format_exc())
            return make_response(jsonify({'msg': 'An internal error has occurred. Please try again later.'}), 500)
        
    # Function to generate a uuid
    def generate_uuid(self) -> str:
        return str(uuid.uuid4())

    # Function to build the twitch auth url
    def build_twitch_auth_url(self, twitch_auth_url: str, twitch_auth_client_id: str, twitch_auth_redirect_uri: str, twitch_auth_response_type: str, twitch_auth_scope: str, activation_code: str) -> str:
        return f'{twitch_auth_url}?client_id={quote(twitch_auth_client_id)}&redirect_uri={quote(twitch_auth_redirect_uri)}&response_type={quote(twitch_auth_response_type)}&scope={quote(twitch_auth_scope)}&force_verify=true&state={quote(str(activation_code))}'

    # Function to validate the payload for twitch gateway creation and returns a string of the channel id
    def validate_twitch_gateway_creation_payload(self, payload) -> str:
        output = None
        # Check if the channel id is set in the request payload
        if 'channel_id' in payload:
            output = payload['channel_id']
        # Else, check if the command string is set in the request payload.
        # If the command string is set, split the command string into a list of commands.
        # The first command in the list is the channel id.
        elif 'command_string' in payload:
            command_string = payload['command_string']
            command_list = self.get_command_params(command_string)
            if command_list is not None and len(command_list) > 0:
                output = command_list[0]

        return output

    # Function to validate the payload for discord gateway creation and returns a DiscordPayload that contains the server id and channel id
    def validate_discord_gateway_creation_payload(self, payload) -> DiscordPayload:
        output = None
        # Check if the server id and channel id is set in the request payload
        if 'server_id' in payload and 'channel_id' in payload:
            output = DiscordPayload(server_id=payload['server_id'], channel_id=payload['channel_id'])
        # Else, check if the command string is set in the request payload.
        # If the command string is set, split the command string into a list of commands.
        # The first command in the list is the server id and the second command is the channel id.
        elif 'command_string' in payload:
            command_string = payload['command_string']
            command_list = self.get_command_params(command_string)
            if command_list is not None and len(command_list) > 1:
                output = DiscordPayload(server_id=command_list[0], channel_id=command_list[1])

        return output
    
