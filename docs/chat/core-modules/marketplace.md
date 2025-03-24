# Marketplace Module

The WaddleBot Marketplace module allows community owners or administrators to install 3rd part modules into a given community that has been registered with waddlebot. The modules function purely per community.

## Relavent Tables

The following list of tables are related to the community module:

| Table Name | List of Fields | Description |
| --- | --- | --- |
| modules | <ul><li>name</li><li>description</li><li>gateway_url</li><li>module_type_id</li><li>metadata</li></ul> | This table keeps track of module related data of both core and non core modules |
| module_types | <ul><li>name</li><li>description</li></ul> | This table contains the different module type descriptions found in WaddleBot, such as Core or Community |
| module_commands | <ul><li>module_id</li><li>command_name</li><li>action_url</li><li>description</li><li>request_method</li><li>request_parameteres</li><li>payload_keys</li><li>req_priv_list</li></ul> | This table is used for module onboarding to capture all the module metadata on a UI and store it on the modules table |

## Modules Table Entry

As stated in the [Modules Table Entry](https://github.com/PenguinCloud/WaddleBot-Core/blob/WaddleBot-Documentation/docs/core-modules/dbm_core_modules.md#modules-table-entry) in the DBM core modules documentation, each module requires an entry in the modules table for interaction to be possible with the listener. 

The following is a JSON representation of what the Marketplace module looks like:

```
{
  "description": "A list of commands that handle the installation of marketplace modules into communities.",
  "gateway_url": "http://127.0.0.1:8000/WaddleDBM/community_modules/",
  "metadata": {
    "!marketplace_install": {
      "action": "http://127.0.0.1:8000/WaddleDBM/community_members/install_by_community_name.json",
      "description": "This command installs a marketplace module into the given community. Example: !marketplace install <my_community> [module_id]",
      "method": "GET",
      "parameters": [
        "community_name"
      ],
      "payload_keys": [
        "module_id"
      ],
      "req_priv_list": [
        "admin"
      ]
    },
    "!marketplace_uninstall": {
      "action": "http://127.0.0.1:8000/WaddleDBM/community_members/uninstall_by_community_name.json",
      "description": "This command uninstalls a module from a community. Example: !marketplace install <my_community> [module_id]",
      "method": "GET",
      "parameters": [
        "community_name"
      ],
      "payload_keys": [
        "module_id"
      ],
      "req_priv_list": [
        "admin"
      ]
    }
  },
  "module_type_id": 1,
  "name": "Marketplace Community"
}
```

## Module Commands

With the module entries discussed in the previous section, below is a list of commands as a brief summary of all the functions tha the marketplace module has to offer:

| Command | Description |
| --- | --- |
| !marketplace install | This command installs a marketplace module into the given community. Example: !marketplace install <my_community> [module_id] |
| !marketplace uninstall | This command uninstalls a module from a community. Example: !marketplace install <my_community> [module_id] |


## Code Source files

The communities module consist of the collowing script files for all its functionality:

- [db.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/models/db.py) (Table declaration)
- [modules.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/controllers/modules.py)
- [module_types.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/controllers/modules_types.py)
- [module_onboarding.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/controllers/module_onboarding.py)