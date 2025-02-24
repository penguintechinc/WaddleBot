from flask import Flask, request, make_response, jsonify, send_file, render_template
from flask_restx import Resource, Api, fields, reqparse, abort, Namespace

import json
import traceback
import os
from datetime import datetime
import base64
import sys
import requests
from re import findall

from dotenv import load_dotenv
from message_sender.twitch_msg import Twitch_Message_Sender
from message_sender.discord_msg import Discord_Message_Sender

from classes.gateway_classes import DiscordPayload

from helpers.helpers import GwHelpers

# Set the log level to INFO
from WaddlebotLibs.botLogger import BotLogger

# CONSTANTS
LOG_LEVEL = "INFO"

# Initiate the logger
log = BotLogger(logFile="gateway_creator.log")
log.fileLogger()

# This scripts handles the creation of a gateway in the application, as a namespace

gateway_creator_namespace = Namespace('gateway-creator', description='Gateway Creator operations')

twitch_creator_model = gateway_creator_namespace.model('Twitch Creator', {
    'channel_id': fields.String(required=False, description='The channel id'),
    'command_string': fields.String(required=False, description='The command string')})

discord_creator_model = gateway_creator_namespace.model('Discord Gateway', {
    'server_id': fields.String(required=False, description='The channel id'),
    'channel_id': fields.String(required=False, description='The channel id'),
    'command_string': fields.String(required=False, description='The command string')})

# Create an instance of the GwHelpers class
gw_helpers = GwHelpers()

# Function route to create a gateway for twitch
@gateway_creator_namespace.route('/twitch/')
class TwitchGateway(Resource):
    @gateway_creator_namespace.expect(twitch_creator_model)
    def post(self):
        try:
            payload = request.json

            gateway_type_name = 'Twitch'
            channel_id = gw_helpers.validate_twitch_gateway_creation_payload(payload=payload)

            # Check if all the payload parameters are set
            if not gateway_type_name:
                return make_response(jsonify({'msg': 'Gateway type name not set'}), 400)
            if not channel_id:
                return make_response(jsonify({'msg': 'No channel_id or command_string provided.'}), 400)

            # Get the gateway servers
            gateway_servers = gw_helpers.get_gateway_servers(gateway_server_get_url=gw_helpers.gateway_server_get_url)

            default_twitch_server = None

            # Get the default twitch server
            for server in gateway_servers:
                if server['server_type'] == 'Twitch':
                    default_twitch_server = server['name']
                    break

            if default_twitch_server is not None:
                # Generate an activation code
                activation_code = gw_helpers.generate_uuid()
                response = requests.post(gw_helpers.gateway_creation_url, json={'gateway_server_name': default_twitch_server, 'gateway_type_name': gateway_type_name, 'channel_id': channel_id, 'activation_key': activation_code})

                # The response payload should be a JSON object and contain a key 'msg'
                response_payload = response.json()
                if 'msg' not in response_payload:
                    return make_response(jsonify({'msg': 'Something went wrong while creating the gateway. Please try again later, or contact a technician for further assistance'}), 500)

                # Return the response payload msg value from the gateway creation service
                msg = response_payload['msg']

                # Check if a status key is present in the response payload. Return a 500 error if it is not present
                if 'status' not in response_payload:
                    return make_response(jsonify({'msg': 'Something went wrong while creating the gateway. Please try again later, or contact a technician for further assistance'}), 500)
                    
                status = response_payload['status']

                # If the gateway was created successfully, send a message to the twitch channel
                if status == 201:
                    # Create the twitch message sender object
                    twitch_message_sender = Twitch_Message_Sender(gw_helpers.twitch_host, int(gw_helpers.twitch_port), gw_helpers.twitch_nick, gw_helpers.twitch_pass, channel_id)
                    # Build the twitch auth url
                    twitch_auth_url = gw_helpers.build_twitch_auth_url(twitch_auth_url=twitch_auth_url, 
                                                                       twitch_auth_client_id=gw_helpers.twitch_auth_client_id, 
                                                                       twitch_auth_redirect_uri=gw_helpers.twitch_auth_redirect_uri, 
                                                                       twitch_auth_response_type=gw_helpers.twitch_auth_response_type, 
                                                                       twitch_auth_scope=gw_helpers.twitch_auth_scope, 
                                                                       activation_code=activation_code)

                    twitch_msg = f"Welcome to WaddleBot, {channel_id}! First of all, please mod WaddleBot on your channel. Then, click on the following link to authenticate your account: {twitch_auth_url}."

                    twitch_message_sender.send_message(twitch_msg)

                    return make_response(jsonify({'msg': msg}), 200)
                else:
                    return make_response(jsonify({'msg': msg}), 500)

        except Exception as e:
            log.error(traceback.format_exc())
            return make_response(jsonify({'msg': 'An internal error has occurred. Please try again later.'}), 500)
        
    # Function route to delete a gateway
    @gateway_creator_namespace.expect(twitch_creator_model)
    def delete(self):
        try:
            payload = request.json

            gateway_type_name = 'Twitch'
            channel_id = gw_helpers.validate_twitch_gateway_creation_payload(payload=payload)

            # Check if all the payload parameters are set
            if not gateway_type_name:
                return make_response(jsonify({'msg': 'Gateway type name not set'}), 400)
            if not channel_id:
                return make_response(jsonify({'msg': 'No channel_id or command_string provided.'}), 400)
            
            # Check that the gateway type is "Twitch" or "Discord", because only twitch and discord is currently supported
            if gateway_type_name not in ['Twitch', 'Discord']:
                return make_response(jsonify({'msg': 'Gateway type not supported. Only Twitch is currently available for support.'}), 400)
            elif gateway_type_name == 'Twitch':
                response = requests.delete(gw_helpers.gateway_deletion_url, json={'gateway_type_name': gateway_type_name, 'channel_id': channel_id})

                # The response payload should be a JSON object and contain a key 'msg'
                response_payload = response.json()
                if 'msg' not in response_payload:
                    return make_response(jsonify({'msg': 'ERROR IN WADDLEBOT DB DELETION'}), 500)

                # Return the response payload msg value from the gateway creation service
                msg = response_payload['msg']

                # Check if a status key is present in the response payload. Return a 500 error if it is not present
                if 'status' not in response_payload:
                    return make_response(jsonify({'msg': 'Something went wrong while deleting the gateway. Please try again later, or contact a technician for further assistance'}), 500)
                    
                status = response_payload['status']

                # If the gateway was deleted successfully, send a message to the twitch channel
                if status == 200:
                    # Create the twitch message sender object
                    twitch_message_sender = Twitch_Message_Sender(gw_helpers.twitch_host, int(gw_helpers.twitch_port), gw_helpers.twitch_nick, gw_helpers.twitch_pass, channel_id)
                    # Send the message to the twitch channel
                    twitch_msg = "Hi there! Your gateway has been deleted successfully. Thank you for using WaddleBot!"
                    twitch_message_sender.send_message(twitch_msg)

                    return make_response(jsonify({'msg': msg}), 200)
                else:
                    return make_response(jsonify({'msg': msg}), 500)

            # return make_response(jsonify({'msg': msg}), 200)
        except Exception as e:
            log.error(traceback.format_exc())
            return make_response(jsonify({'msg': 'An internal error has occurred. Please try again later.'}), 500)
            

# Function route to create a gateway
@gateway_creator_namespace.route('/discord/')
class DiscordGateway(Resource):
    @gateway_creator_namespace.expect(discord_creator_model)
    def post(self):
        try:
            payload = request.json

            gateway_type_name = "Discord"

            payloadArgs = gw_helpers.validate_discord_gateway_creation_payload(payload=payload)

            # Check if the payloadArgs is None
            if payloadArgs is None:
                return make_response(jsonify({'msg': 'No server_id or channel_id or command_string provided'}), 400)

            server_id = payloadArgs.server_id
            channel_id = payloadArgs.channel_id

            # If the gateway type is Discord, create a new gateway server and then create the gateway
            if gateway_type_name == 'Discord':
                # Create a new gateway server
                response = requests.post(gw_helpers.gateway_server_create_url, json={'name': server_id, 'server_type_name': 'Discord', 'server_id': server_id, 'server_nick': 'waddlebot'})

                # The response payload should be a JSON object and contain a key 'msg'
                response_payload = response.json()
                if 'msg' not in response_payload:
                    return make_response(jsonify({'msg': 'Something went wrong while creating the gateway. Please try again later, or contact a technician for further assistance'}), 500)
                
                log.info(response_payload)
                # If the server creation process was successful, create the gateway route
                if response_payload['status'] == 201:
                    log.info(f"Server {server_id} created successfully. Creating gateway now.")

                    # Generate an activation code
                    activation_code = gw_helpers.generate_uuid()
                    response = requests.post(gw_helpers.gateway_creation_url, json={'gateway_server_name': server_id, 'gateway_type_name': gateway_type_name, 'channel_id': channel_id, 'activation_key': activation_code})

                    log.info("Got a response from the gateway creation service")

                    # The response payload should be a JSON object and contain a key 'msg'
                    response_payload = response.json()
                    if 'msg' not in response_payload:
                        return make_response(jsonify({'msg': 'Something went wrong while creating the gateway. Please try again later, or contact a technician for further assistance'}), 500)

                    log.info("Got a message from the gateway creation service")

                    # Return the response payload msg value from the gateway creation service
                    msg = response_payload['msg']

                    # Check if a status key is present in the response payload. Return a 500 error if it is not present
                    if 'status' not in response_payload:
                        return make_response(jsonify({'msg': 'Something went wrong while creating the gateway. Please try again later, or contact a technician for further assistance'}), 500)
                        
                    status = response_payload['status']

                    log.info(f"Got a status of {status}")

                    # If the gateway was created successfully, send a message to the discord channel
                    if status == 201:
                        log.info("Starting the discord message sending process")

                        # Create a message to send to the discord channel
                        discord_msg = f"Welcome to WaddleBot, {server_id}! Please follow the following link to add the bot to your server: {gw_helpers.discord_bot_invite_url}. Afterwards, your set up is complete! Enjoy using WaddleBot!"

                        # Create the discord message sender object
                        log.info("Creating discord message sender object")
                        discord_message_sender = Discord_Message_Sender(gw_helpers.discord_token, server_id, discord_msg)


                        # Send the message to the discord channel
                        log.info(f"Sending message to discord channel {server_id}")
                        discord_message_sender.send_message()

                        return make_response(jsonify({'msg': msg}), 200)
                    else:
                        return make_response(jsonify({'msg': msg}), 500)
                else:
                    log.info("AN ERROR OCURRED")
                    if 'msg' in response_payload:
                        return make_response(jsonify({'msg': response_payload['msg']}), 500)
                    return make_response(jsonify({'msg': 'Something went wrong while creating the gateway. Please try again later, or contact a technician for further assistance.'}), 500)
            else:
                return make_response(jsonify({'msg': 'Gateway type not supported. Only Twitch and Discord is currently available for support.'}), 400)

            # return make_response(jsonify({'msg': msg}), 200)
        except Exception as e:
            log.error(f"An error occurred: {str(e)}")
            return make_response(jsonify({'msg': 'An internal error has occurred. Please try again later.'}), 500)
        
    # Function route to delete a gateway
    @gateway_creator_namespace.expect(discord_creator_model)
    def delete(self):
        try:
            payload = request.json

            gateway_type_name = "Discord"

            payloadArgs = gw_helpers.validate_discord_gateway_creation_payload(payload=payload)

            # Check if the payloadArgs is None
            if payloadArgs is None:
                return make_response(jsonify({'msg': 'No server_id or channel_id or command_string provided'}), 400)

            server_id = payloadArgs.server_id
            channel_id = payloadArgs.channel_id
                
            if gateway_type_name == 'Discord':
                response = requests.delete(gw_helpers.gateway_server_delete_url + f'{server_id}')

                # The response payload should be a JSON object and contain a key 'msg'
                response_payload = response.json()
                if 'msg' not in response_payload:
                    return make_response(jsonify({'msg': 'An error occurred while deleting the gateway server. Please try again later, or contact a technician for further assistance'}), 500)

                # After the server was successfully deleted, delete the gateway
                response = requests.delete(gw_helpers.gateway_deletion_url, json={'gateway_type_name': gateway_type_name, 'channel_id': channel_id})

                # Return the response payload msg value from the gateway creation service
                msg = response_payload['msg']

                # Check if a status key is present in the response payload. Return a 500 error if it is not present
                if 'status' not in response_payload:
                    return make_response(jsonify({'msg': 'Something went wrong while deleting the gateway. Please try again later, or contact a technician for further assistance'}), 500)
                    
                status = response_payload['status']

                # If the gateway was deleted successfully, send a message to the discord channel
                if status == 200:
                    return make_response(jsonify({'msg': msg}), 200)
                else:
                    return make_response(jsonify({'msg': msg}), 500)
            else:
                return make_response(jsonify({'msg': 'Gateway type not supported. Only Twitch and Discord is currently available for support.'}), 400)

        except Exception as e:
            log.error(f"An error occurred: {str(e)}")
            return make_response(jsonify({'msg': 'An internal error has occurred. Please try again later.'}), 500)