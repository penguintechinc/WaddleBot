import toml
import requests
import os
from dotenv import load_dotenv
import subprocess
from libs.botLogger import BotLogger

# constants
ROOT_FOLDER = os.path('/opt/manager/')
LOG_LEVEL = "INFO"

# Initiate the logger
log = BotLogger("restart", LOG_LEVEL)

# This function will retrieve the MAT gateways from the API and compare them with the existing 
# matterbridge.toml accounts found in the configuration file. If there are any new gateways, 
# the function will kill the matterbridge process and run the entrypoint.sh script to start 
# the matterbridge process with the new configuration file that gets generated from that shell script.
def main():
    # Check if the .env file exists
    try:
        # load_dotenv()

        # If the .env file exists, get the values of the environment variables
        # and store them in variables
        mat_url = os.getenv('GATEWAYS_GET_URL')

        # Get the gateways from the MAT API
        gateways = get_gateways(mat_url)

        # Check if the gateways list is not empty
        if gateways is None:
            log.error("Failed to get gateways from MAT API")
            return "Failed to get gateways from MAT API"
        
        # Get the existing gateway accounts from the matterbridge.toml file
        # accounts = get_gateway_accounts()
        
        # Get the existing gateway channels from the matterbridge.toml file
        channels = get_gateway_channels()

        # Check if the accounts list is not empty
        # if accounts is None:
        #     return "Failed to get gateway accounts from matterbridge.toml"

        # Check if the channels list is not empty
        if channels is None:
            log.error("Failed to get gateway channels from matterbridge.toml")
            return "Failed to get gateway channels from matterbridge.toml"

        log.debug("The existing channels are: ")
        log.debug(channels)
        # log.debug("The found gateways are: ")
        # log.debug(gateways)
        # log.debug only the account key from the gateways list
        gAccounts = [gateway['channel_id'] for gateway in gateways]
        log.debug(gAccounts)

        # Check if there are any new gateways
        new_gateways = [gateway for gateway in gateways if gateway['channel_id'] not in channels]

        # If there are new gateways, stop the matterbridge process and start it with the new configuration
        if new_gateways:
            stop_matterbridge()
            start_matterbridge('entrypoint.sh')
            return "Successfully restarted matterbridge with new configuration"
        
        return "No new gateways found"
    except Exception as e:
        return str(e)


# Function to get the gateways from the API
def get_gateways(url):
    log.debug("Getting gateways from MAT API")
    log.debug("The URL is: ", url)

    # Make a GET request to the MAT API to get the gateways
    response = requests.get(url, timeout=30)

    gateways = []

    # Check if the response is successful
    if response.status_code == 200:
        # Check that the response is in JSON format and that the key "data" exists
        if response.headers['Content-Type'] == 'application/json' and 'data' in response.json():
            response_json = response.json()
            gateways = response_json['data']
    else:
        log.debug("Failed to get gateways from MAT API")
        return None

    # Check if the gateways list is not empty
    if len(gateways) == 0:
        log.debug("No gateways found")
        return None
    
    return gateways


def pretty(d, indent=0):
        for key, value in d.items():
            log.debug('\t' * indent + str(key))
            if isinstance(value, dict):
                pretty(value, indent+1)
            else:
                log.debug('\t' * (indent+1) + str(value))

# Function to read the existing matterbridge.toml file and return all the instances of the gateway.inout's account variables
def get_gateway_accounts():
    log.debug("Getting gateway accounts from matterbridge.toml")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, 'matterbridge.toml')

    # Read the existing matterbridge.toml file
    with open(file_path, 'r') as file:
        data = file.read()

    # Parse the toml file
    toml_data = toml.loads(data)

    # log.debug("The toml data is: ")
    # pretty(toml_data)

    # Get all the instances of the gateway.inout's account variables
    accounts = []

    # Check that the toml_data contains the key "gateway"
    if 'gateway' in toml_data:
        gateway = toml_data['gateway']
        
        # Gateway is a list of dictionaries. Each dictionary represents a gateway. 
        # Check if each dictionary contains the key "inout"
        for g in gateway:
            if 'inout' in g:
                inout = g['inout']
                
                # inout is a list of dictionaries. Each dictionary represents an inout. 
                # Check if each dictionary contains the key "account"
                for i in inout:
                    if 'account' in i:
                        accounts.append(i['account'])

    return accounts

# Function to read the existing matterbridge.toml file and return all the instances of the gateway.inout's channel variables
def get_gateway_channels():
    log.debug("Getting gateway channels from matterbridge.toml")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, 'matterbridge.toml')

    # Read the existing matterbridge.toml file
    with open(file_path, 'r') as file:
        data = file.read()

    # Parse the toml file
    toml_data = toml.loads(data)

    # log.debug("The toml data is: ")
    # pretty(toml_data)

    # Get all the instances of the gateway.inout's account variables
    channels = []

    # Check that the toml_data contains the key "gateway"
    if 'gateway' in toml_data:
        gateway = toml_data['gateway']
        
        # Gateway is a list of dictionaries. Each dictionary represents a gateway. 
        # Check if each dictionary contains the key "inout"
        for g in gateway:
            if 'inout' in g:
                # inout is a list of dictionaries. Each dictionary represents an inout. 
                # Check if each dictionary contains the key "account"
                for i in g['inout']:
                    if 'channel' in i:
                        channels.append(i['channel'])

    return channels

# This function stops the matterbridge.exe process, if the process is running
def stop_matterbridge():
    # Check if the matterbridge process is running
    process = subprocess.Popen(['pgrep', 'matterbridge'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    # If the process is running, stop it
    if stdout:
        process_id = int(stdout.decode().strip())
        subprocess.run(['kill', str(process_id)])
        log.debug("Stopped matterbridge process")
    else:
        log.debug("matterbridge process is not running")

# This function executes the entrypoint.sh script to start the matterbridge.exe process
def start_matterbridge(shFile):
    # Check if the matterbridge process is running
    process = subprocess.Popen(['pgrep', 'matterbridge'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    if stdout:
        log.debug("matterbridge process is running")
        return

    # Execute the entrypoint.sh script to start the matterbridge process
    entrypoint_path = os.path.join(ROOT_FOLDER, shFile)

    log.debug("The entrypoint path is: ", entrypoint_path)
    # subprocess.run(['sh', entrypoint_path])
    # os.popen('sh ' + entrypoint_path)
    process = subprocess.Popen(['sh', entrypoint_path])
    log.debug(f"Started matterbridge process with PID: {process.pid}")
    log.debug("Started matterbridge process")


if __name__ == '__main__':
    # msg = main()
    # log.debug(msg)
    log.debug("The restart.py script is running")
