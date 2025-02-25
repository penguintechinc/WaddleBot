# Command Alias Module Module

The WaddleBot Command Alias module, allows users of a given community to add an alias to a given command, allowing users in that community to execute certain commands that are bound to those aliases. 

For example, lets say we have the following command that executes its own unique function:

`!test command`

Now, lets add an alias to it called "!alias command". When we run the new alias command in that community, we will get the same procedure and execution as the above command its bound to.

Note that any command aliases that are created per community, only function on those specific communities. 

## Relavent Tables

The following list of tables are related to the Command Alias module:

| Table Name | List of Fields | Description |
| --- | --- | --- |
| alias_commands | <ul><li>community_id</li><li>alias_val</li><li>command_val</li></ul> | This module allows identities to create aliases for commands on a per community basis. |

## Modules Table Entry

As stated in the [Modules Table Entry](https://github.com/PenguinCloud/WaddleBot-Core/blob/WaddleBot-Documentation/docs/core-modules/dbm_core_modules.md#modules-table-entry) in the DBM core modules documentation, each module requires an entry in the modules table for interaction to be possible with the listener. 

The following is a JSON representation of what the Alias Commands module looks like:

```
{
    "description": "A list of commands to manage Command Aliases.",
    "gateway_url": "http://127.0.0.1:8000/WaddleDBM/",
    "metadata": {
        "!alias": {
            "action":"http://127.0.0.1:8000/WaddleDBM/alias_commands/get_by_alias.json",
            "description":"This command gets a alias commands from a given value. Example: !alias [!alias]",
            "method":"GET",
            "parameters":[
                "community_name"
            ],
            "payload_keys": [
                "alias"
            ],
            "req_priv_list":[]
        },
        "!alias_delete":{
            "action":"http://127.0.0.1:8000/WaddleDBM/alias_commands/delete_by_alias.json",
            "description":"This command delete a alias commands from a given value. Example: !alias delete [!alias]",
            "method":"DELETE",
            "parameters":[
                "community_name"
            ],
            "payload_keys":[
                "alias"
            ],
            "req_priv_list":[]
        },
        "!alias_get_all":{
            "action":"http://127.0.0.1:8000/WaddleDBM/alias_commands/get_all.json",
            "description":"This command gets all the alias commandss for the current community.",
            "method":"GET",
            "parameters":[
                "community_name"
            ],
            "payload_keys":[],
            "req_priv_list":[]
        },
        "!alias_set":{
            "action":"http://127.0.0.1:8000/WaddleDBM/alias_commands/set_alias_command.json",
            "description":"This command maps an existing waddlebot command to an alias. Example: !alias set [!alias] [!command]",
            "method":"POST",
            "parameters":["community_name"],
            "payload_keys":["alias","command"],
            "req_priv_list":[]
            }
        },
    "module_type_id": 1,
    "name": "Alias Commands"
}
```

## Module Commands

With the module entries discussed in the previous section, below is a list of commands as a brief summary of all the functions tha the Alias Commands module has to offer:

| Command | Description |
| --- | --- |
| !alias | This command gets a alias commands from a given value. Example: !alias [!alias] |
| !alias delete | This command delete a alias commands from a given value. Example: !alias delete [!alias] |
| !alias get all | This command gets all the alias commandss for the current community. |
| !alias set | This command maps an existing waddlebot command to an alias. Example: !alias set [!alias] [!command] |

## Code Source files

The alias commands module consist of the collowing script files for all its functionality:

- [db.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/models/db.py) (Table declaration)
- [alias_commands.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/controllers/alias_commands.py)