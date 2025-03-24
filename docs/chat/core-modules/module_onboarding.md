# Module Onboarding Module

The WaddleBot Module onboarding module, allows identities to onboard new modules into waddlebot that can be then later installed on a per community basis. The onboarding module contains a helpful UI to easily input all the necessary fields.

## Relavent Tables

The following list of tables are related to the module onboarding module:

| Table Name | List of Fields | Description |
| --- | --- | --- |
| modules | <ul><li>name</li><li>description</li><li>gateway_url</li><li>module_type_id</li><li>metadata</li></ul> | This table keeps track of module related data of both core and non core modules |
| module_commands | <ul><li>module_id</li><li>command_name</li><li>action_url</li><li>description</li><li>request_method</li><li>request_parameteres</li><li>payload_keys</li><li>req_priv_list</li></ul> | This table is used for module onboarding to capture all the module metadata on a UI and store it on the modules table |

## Modules Table Entry

As stated in the [Modules Table Entry](https://github.com/PenguinCloud/WaddleBot-Core/blob/WaddleBot-Documentation/docs/core-modules/dbm_core_modules.md#modules-table-entry) in the DBM core modules documentation, each module requires an entry in the modules table for interaction to be possible with the listener. 

The following is a JSON representation of what the Module Onboarding module looks like:

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
      },
      "!marketplace_onboard_module": {
          "action": "http://127.0.0.1:8000/WaddleDBM/modules/start_module_onboard.json",
          "description": "This command starts the onboarding process for a module, by displaying a link to a module onboarding form. Example: !marketplace onboard module",
          "method": "GET",
          "parameters": [],
          "payload_keys": [],
          "req_priv_list": []
      }

  },
  "module_type_id": 1,
  "name": "Marketplace Community"
}
```

## Module Commands

With the module entries discussed in the previous section, below is a list of commands as a brief summary of all the functions tha the module onboarding module has to offer:

| Command | Description |
| --- | --- |
| !marketplace onboard module | This command starts the onboarding process for a module, by displaying a link to a module onboarding form. Example: !marketplace onboard module |

## Code Source files

The communities module consist of the collowing script files for all its functionality:

- [db.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/models/db.py) (Table declaration)
- [modules.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/controllers/modules.py)
- [module_onboarding.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/controllers/module_onboarding.py) (Module Onboarding Controller)
- [onboarding_form.html](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/views/module_onboarding/onboard_form.html) (Onboarding form view)
- [manage_commands.html](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/views/module_onboarding/manage_commands.html) (Form to add new commands to the given module)
