# Gateway Manager Module

The WaddleBot gateway manager is a Flask Rest API that allows users to create gateways for new platform channels and servers to be linked to waddlebot. Waddlebot primarily uses [matterbridge](https://github.com/42wim/matterbridge) for communication between different platforms. This module essentially assists in creating the Matterbridge configuration file that matterbridge requires to setup gateways to the correct channels upon activation of the core module. The [WaddleBot-Configurator](https://github.com/PenguinCloud/WaddleBot-Core/tree/main/modules/WaddleBot-Configurator) handles the creation of the config file. 

## Relavent Tables

The following list of tables are related to the gateway manager module:

| Table Name | List of Fields | Description |
| --- | --- | --- |
| routing_gateways | <ul><li>gateway_server</li><li>channel_id</li><li>gateway_type</li><li>activation_key</li><li>is_active</li></ul> | This table stores all the created gateways from this module |
| gateway_types | <ul><li>type_name</li><li>description</li></ul> | This table keeps track of the different routing gateway types, so that when new routing gateways are setup, the core can properly keep track of which config options to use. |
| gateway_servers | <ul><li>name</li><li>server_id</li><li>server_nick</li><li>server_type</li><li>protocol</li></ul> | Gateway servers contain a collaction of server related data that tells Matterbridge which platform servers to communicate with. |
| gateway_server_types | <ul><li>type_name</li><li>description</li></ul> | This table keeps track of the different types of platform servers that Matterbridge can communicate with, such as discord, or twitch |
| gateway_accounts | <ul><li>account_name</li><li>account_type</li><li>is_default</li></ul> | This table stores the accounts that the current version of matterbridge uses for waddlebot's purposes, containing all the necessary config to communicate with a specific platform. More information can be found [here](https://github.com/42wim/matterbridge/wiki/How-to-create-your-config) |
| account_types | <ul><li>type_name</li><li>description</li></ul> | This table stores the relevant account types of Matterbridge, to determine what kind of connection types the gateways are, such as IRC or discord |


## Modules Table Entry

As stated in the [Modules Table Entry](https://github.com/PenguinCloud/WaddleBot-Core/blob/WaddleBot-Documentation/docs/core-modules/dbm_core_modules.md#modules-table-entry) in the DBM core modules documentation, each module requires an entry in the modules table for interaction to be possible with the listener. 

The following is a JSON representation of what the Gateway Manager module looks like:

```
{
  "description": "A list of commands to handle the creation and deletion of gateway routes",
  "gateway_url": "http://127.0.0.1:5000/gateway-creator/",
  "metadata": {
    "!gateway_add": {
      "action": "http://127.0.0.1:5000/gateway-creator/",
      "description": "This command creates a new route for a given platform and channel. Example: !route add [platform] [channel]",
      "method": "POST",
      "parameters": [],
      "payload_keys": [
        "gateway_type_name",
        "channel_id"
      ],
      "req_priv_list": [
        "admin"
      ]
    },
    "!gateway_rem": {
      "action": "http://127.0.0.1:5000/gateway-creator/",
      "description": "This command removes a route for a given platform and channel. Example: !route rem [platform] [channel]",
      "method": "DELETE",
      "parameters": [],
      "payload_keys": [
        "gateway_type_name",
        "channel_id"
      ],
      "req_priv_list": [
        "admin"
      ]
    }
  },
  "module_type_id": 1,
  "name": "Gateway Manager"
}
```

## Module Commands

With the module entries discussed in the previous section, below is a list of commands as a brief summary of all the functions tha the community module has to offer:

| Command | Description |
| --- | --- |
| !gateway add | This command creates a new route for a given platform and channel. Example: !route add [platform] [channel] |
| !gateway rem | This command removes a route for a given platform and channel. Example: !route rem [platform] [channel] |

## Code Source files

The communities module consist of the collowing script files for all its functionality:

- [db.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/models/db.py) (Table declaration)
- [app.py](https://github.com/PenguinCloud/WaddleBot-Core/blob/main/modules/WaddleBot-Gateway-Manager/app/app.py) (The main gateway manager python application in the core module)
- [routing_gateways.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/controllers/routing_gateways.py)
- [gateway_servers.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/controllers/gateway_servers.py)
- [gateway_server_types.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/controllers/gateway_server_types.py)
- [gateway_types.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/controllers/gateway_types.py)
