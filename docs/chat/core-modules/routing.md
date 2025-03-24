# Routing Module

The WaddleBot routing module allows routes to be created between communities and platform channels, allowing only certain communities to be accessed by certain platforms.

## Relavent Tables

The following list of tables are related to the Routing module:

| Table Name | List of Fields | Description |
| --- | --- | --- |
| routing | <ul><li>channel</li><li>community_id</li><li>routing_gateway_ids</li><li>aliases</li></ul> | A table containing all the routing gateways that a community has access to. |

## Modules Table Entry

As stated in the [Modules Table Entry](https://github.com/PenguinCloud/WaddleBot-Core/blob/WaddleBot-Documentation/docs/core-modules/dbm_core_modules.md#modules-table-entry) in the DBM core modules documentation, each module requires an entry in the modules table for interaction to be possible with the listener. 

The following is a JSON representation of what the Routing module looks like:

```
{
  "description": "A list of commands to handle the creation and deletion of routes between communities",
  "gateway_url": "http://127.0.0.1:8000/WaddleDBM/",
  "metadata": {
    "!route_add": {
      "action": "http://127.0.0.1:8000/WaddleDBM/routing/add_route_to_community.json",
      "description": "This command adds a channel to a community. Example: !route add [community name]",
      "method": "PUT",
      "parameters": [
        "channel_id",
        "account"
      ],
      "payload_keys": [
        "community_name"
      ],
      "req_priv_list": [
        "admin"
      ]
    },
    "!route_rem": {
      "action": "http://127.0.0.1:8000/WaddleDBM/routing/remove_route_from_community.json",
      "description": "This command removes a channel from a community. Example: !route rem [community name]",
      "method": "DELETE",
      "parameters": [
        "channel_id",
        "account"
      ],
      "payload_keys": [
        "community_name"
      ],
      "req_priv_list": [
        "admin"
      ]
    }
  },
  "module_type_id": 1,
  "name": "Routing Manager"
}
```

## Module Commands

With the module entries discussed in the previous section, below is a list of commands as a brief summary of all the functions tha the community module has to offer:

| Command | Description |
| --- | --- |
| !route add | This command adds a channel to a community. Example: !route add [community name] |
| !route_rem | This command removes a channel from a community. Example: !route rem [community name] |

## Code Source files

The communities module consist of the collowing script files for all its functionality:

- [db.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/models/db.py) (Table declaration)
- [routing.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/controllers/routing.py)