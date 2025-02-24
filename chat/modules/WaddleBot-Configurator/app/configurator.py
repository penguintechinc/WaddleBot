import toml
import requests
import os


from libs.botLogger import BotLogger

# CONSTANTS
LOG_LEVEL = "INFO"

# Initiate the logger
log = BotLogger("configurator", LOG_LEVEL)

from dataclasses import dataclass, asdict

# Declare the available data classes
@dataclass
class gateway():
    gateway_type: str
    gateway_server: str
    channel_id: str
    is_active: bool

@dataclass
class gateway_server():
    name: str
    server_id: str
    server_nick: str
    server_type: str

class configuration():
    def __init__(self):
        self.gw_servers = gateway_server
        self.gw = gateway

# The main function that will be called when the script is run
    def main(self) -> str:
        # Check if the .env file exists
        try:
            # If the .env file exists, get the values of the environment variables
            # and store them in variables
            log.info("Getting MAT configuration data from environment variables")

            gateway_servers_url = os.getenv('GATEWAY_SERVERS_GET_URL')
            gateways_url = os.getenv('GATEWAYS_GET_URL')
            discord_token = os.getenv('DISCORD_TOKEN')
            twitch_token = os.getenv('TWITCH_TOKEN')
            api_name = os.getenv('API_NAME')
            api_address = os.getenv('API_ADDRESS')

            log.info("Executing requests to get MAT configuration data")

            # Get the gateway servers and their gateways
            gateway_servers = get_gateway_servers(gateway_servers_url)
            gateways = get_gateways(gateways_url)

            # Check if the gateway servers and gateways are not empty
            if (gateway_servers is None or gateways is None) or (len(gateway_servers) == 0 or len(gateways) == 0):
                return "Failed to get gateway servers or gateways"

            log.info("Finished the requests to get MAT configuration data")

            script_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(script_dir, 'mat_template.toml')

            try:
                log.info("Reading MAT template file")

                # Load the template toml file "mat_template.toml" in the "templates" folder
                with open(file_path, 'r') as matfile:
                    template = matfile.read()

                    # Close the file
                    matfile.close()

                    # Replace the placeholders in the template file with the environment variables
                    template = template.replace('{{api_gateway_name}}', api_name)
                    template = template.replace('{{api_address}}', api_address)

                    template += '\n'

                    log.info("Creating Twitch Server toml object")
                    # Create the twitch server toml object string
                    twitch_server_toml = create_twitch_server(gateway_servers, os.path.join(script_dir, 'twitch_server_template.toml'), twitch_token)

                    # Add the twitch server to the template file
                    template += twitch_server_toml

                    log.info("Creating Discord Server toml object")
                    # Create the discord server toml object string
                    discord_server_toml = create_discord_server(gateway_servers, os.path.join(script_dir, 'discord_server_template.toml'), discord_token)

                    # Add the discord server to the template file
                    template += discord_server_toml

                    log.info("Creating Gateway toml object")
                    # Create the global community toml object string
                    gateway_inout_toml = create_gateways(gateways, api_name)

                    # Add the global community to the template file
                    template += gateway_inout_toml

                    # Get the path of the script directory and the output file path
                    out_file_path = os.path.join(script_dir, 'matterbridge.toml')

                    try:
                        # Write the new toml file "matterbridge.toml"
                        with open(out_file_path, 'w') as file:
                            file.write(template)

                            # Close the file
                            file.close()

                        log.info("Successfully created MAT configuration file")
                    except Exception as e:
                        log.error("Failed to write MAT configuration file: " + str(e))
                        return(str(e))

                msg = "Successfully created MAT configuration file"
                return(msg)
            
            except Exception as e:
                log.error("Failed to read MAT template file: " + str(e))
                return(str(e))

        except Exception as e:
            log.error("SOMETHING WENT WRONG: " + str(e))
            return(str(e))


    # Function to create the twitch server toml object from the template twitch file
    def create_twitch_server(self, gateway_servers: list[gateway_server], file: str, twitch_token: str) -> str:
        toml_string = ""

        log.info("Creating twitch server toml object")

        log.debug(gateway_servers)

        try:
            # Open the twitch template file
            with open(file, 'r') as f:
                template_str = f.read()

                # Loop through the gateway servers and for each server that is of type "Twitch", create a twitch server object
                for server in gateway_servers:
                    if server['server_type'] == 'Twitch':
                        # Replace all special characters and spaces in the server name with underscores
                        server['name'] = server['name'].replace(' ', '_')
                        server['name'] = server['name'].replace("'", '')

                        twitch_server = template_str.replace('{{gateway_name}}', server['name'])
                        twitch_server = twitch_server.replace('{{server}}', server['server_id'])
                        twitch_server = twitch_server.replace('{{nick}}', server['server_nick'])
                        twitch_server = twitch_server.replace('{{token}}', twitch_token)
                        twitch_server += '\n'
                        toml_string += twitch_server

            log.info("Successfully created twitch server toml object")
            return toml_string
        except Exception as e:
            log.error("Failed to create twitch server toml object: " + str(e))
            return(str(e))

    # Function to create the discord server toml object from the template discord file
    def create_discord_server(self, gateway_servers: list[gateway_server], file: str, discord_token: str) -> str:
        toml_string = "\n[discord]\n"

        log.info("Creating discord server toml object")

        try:
            # Open the discord template file
            with open(file, 'r') as f:
                template_str = f.read()

                # Loop through the gateway servers and for each server that is of type "Discord", create a discord server object
                for server in gateway_servers:
                    if server['server_type'] == 'Discord':
                        # Replace all special characters and spaces in the server name with underscores
                        server['name'] = server['name'].replace(' ', '_')
                        server['name'] = server['name'].replace("'", '')

                        discord_server = template_str.replace('{{gateway_name}}', server['name'])
                        discord_server = discord_server.replace('{{server}}', server['server_id'])
                        discord_server = discord_server.replace('{{token}}', discord_token)
                        discord_server += '\n'
                        toml_string += discord_server

            log.info("Successfully created discord server toml object")
            return toml_string
        except Exception as e:
            log.error("Failed to create discord server toml object: " + str(e))
            return(str(e))

    # Function to create a gateway opject for each gateway in the list of gateways
    def create_gateways(self, gateways: list[gateway], api_name: str) -> str:
        toml_string = ""
        log.info("Creating gateway toml object")

        # Create all the gateway objects
        for gateway in gateways:
            channel_id = gateway['channel_id']

            # Create the first part of the toml string to contain the gateway name
            toml_string += f'\n[[gateway]]\nname = "{channel_id}"\nenable=true\n'

            # Replace all special characters and spaces in the server name with underscores
            gateway_server = gateway['gateway_server']
            gateway_server = gateway_server.replace(' ', '_')
            gateway_server = gateway_server.replace("'", '')

            # Get the gateway type from the gateway
            gateway_type = gateway['gateway_type']
            if gateway_type == "Discord":
                log.info("Discord gateway found")
                gateway_type = "discord"
            elif gateway_type == "Twitch":
                log.info("Twitch gateway found")
                gateway_type = "irc"

            # Create the second part of the toml string to contain the gateway inout objects
            toml_string += f'\n[[gateway.inout]]\naccount="{gateway_type}.{gateway_server}"\nchannel="{channel_id}"\n'

            # Add the api gateway inout toml object string
            toml_string += f'\n[[gateway.inout]]\naccount = "api.{api_name}"\nchannel = "api"\n'

        return toml_string

    # Function to get the gateways from the API
    def get_gateways(self, url: str) -> list[gateway]:
        try:
            log.info("Getting gateways from MAT API")

            # Make a GET request to the MAT API to get the gateways
            response = requests.get(url)

            gateways = []

            log.info("Got a response from MAT API")
            log.info(response.json())

            # Check if the response is successful
            if response.status_code == 200:
                # Check that the response is in JSON format and that the key "data" exists
                if response.headers['Content-Type'] == 'application/json' and 'data' in response.json():
                    response_json = response.json()
                    gateways = response_json['data']
            else:
                log.info("Failed to get gateways from MAT API")
                return None

            # Check if the gateways list is not empty
            if len(gateways) == 0:
                log.info("No gateways found")
                return None
            
            log.info("Successfully got gateways from MAT API")
            return gateways
        except Exception as e:
            log.error("Failed to get gateways from WaddleDBM: " + str(e))
            return None

    # Function to get the gateway servers from the API
    def get_gateway_servers(self, url: str) -> list[gateway_server]:
        try:
            log.info("Getting gateway servers from MAT API")

            # Make a GET request to the MAT API to get the gateway servers
            response = requests.get(url)

            gateway_servers = []

            log.info("Got a response from MAT API")
            log.info(response.json())

            # Check if the response is successful
            if response.status_code == 200:
                # Check that the response is in JSON format and that the key "data" exists
                if response.headers['Content-Type'] == 'application/json' and 'data' in response.json():
                    response_json = response.json()
                    gateway_servers = response_json['data']
            else:
                log.info("Failed to get gateway servers from MAT API")
                return None

            # Check if the gateway servers list is not empty
            if len(gateway_servers) == 0:
                log.info("No gateway servers found")
                return None
            
            log.info("Successfully got gateway servers from MAT API")
            return gateway_servers
        except Exception as e:
            log.error("Failed to get gateway servers from WaddleDBM: " + str(e))
            return None

if __name__ == "__main__": 
    msg = configuration
    msg.main(args=None)
    log.debug(msg)

