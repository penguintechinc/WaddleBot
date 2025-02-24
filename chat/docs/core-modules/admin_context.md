# Admin Context Module

The waddlebot admin context module allows community admins to "login" to an admin session, where they can access and execute any commands in a community that require "admin" privilages. When a context is created, a unique GUID is allocated for that user with an expiry date. If the session expires, the user needs to "login" again to make use of admin commands again.

## Relavent Tables

The following list of tables are related to the admin_context module:

| Table Name | List of Fields | Description |
| --- | --- | --- |
| admin_contexts | <ul><li>identity_id</li><li>community_id</li><li>session_token</li><li>session_expires</li></ul> | Keeps track of administrator sessions that community admins need to sign into to access "admin" level commands of a community. |

## Modules Table Entry

As stated in the [Modules Table Entry](https://github.com/PenguinCloud/WaddleBot-Core/blob/WaddleBot-Documentation/docs/core-modules/dbm_core_modules.md#modules-table-entry) in the DBM core modules documentation, each module requires an entry in the modules table for interaction to be possible with the listener. 

The following is a JSON representation of what the Admin Context module looks like:

```
{
  "description": "A list of commands to manage admin contexts.",
  "gateway_url": "http://127.0.0.1:8000/WaddleDBM/",
  "metadata": {
    "!admin_login": {
      "description": "This command logs an admin into an admin context to run admin commands. User must be an admin of the community.",
      "method": "POST",
      "action": "http://127.0.0.1:8000/WaddleDBM/admin_context/create_session.json",
      "parameters": [
        "community_name"
      ],
      "payload_keys": [
        "identity_name"
      ],
      "req_priv_list": []
    },
    "!admin_logout": {
      "description": "This command logs an admin out of an admin context. User must be an admin of the community.",
      "method": "POST",
      "action": "http://127.0.0.1:8000/WaddleDBM/admin_context/delete_by_community_and_identity.json",
      "parameters": [
        "community_name"
      ],
      "payload_keys": [
        "identity_name"
      ],
      "req_priv_list": []
    }
  },
  "module_type_id": 1,
  "name": "Admin Context"
}
```

## Module Commands

With the module entries discussed in the previous section, below is a list of commands as a brief summary of all the functions tha the admin context module has to offer:

| Command | Description |
| --- | --- |
| !admin login | This command logs an admin into an admin context to run admin commands. User must be an admin of the community. |
| !admin logout | This command logs an admin out of an admin context. User must be an admin of the community. |

## Code Source files

The admin context module consist of the collowing script files for all its functionality:

- [db.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/models/db.py) (Table declaration)
- [admin_context.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/controllers/admin_context.py)