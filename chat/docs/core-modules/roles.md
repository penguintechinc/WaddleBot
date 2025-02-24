# Roles Module

The WaddleBot roles module allows for the allocation of roles to individual community member identities that sets their individual privilages. 

Creating a new community sets a list of default roles. These roles are created according to the default roles set in [Waddlebot's Default Roles](https://github.com/PenguinCloud/WaddleBot-Core/blob/WaddleBot-Documentation/docs/core-modules/dbm_core_modules.md#db-initialization)

## Relavent Tables

The following list of tables are related to the roles module:

| Table Name | List of Fields | Description |
| --- | --- | --- |
| roles | <ul><li>name</li><li>community_id</li><li>description</li><li>priv_list</li><li>requirements</li></ul> | Contains a list of all the roles that is available to a community. Determines module access. |

## Modules Table Entry

As stated in the [Modules Table Entry](https://github.com/PenguinCloud/WaddleBot-Core/blob/WaddleBot-Documentation/docs/core-modules/dbm_core_modules.md#modules-table-entry) in the DBM core modules documentation, each module requires an entry in the modules table for interaction to be possible with the listener. 

The following is a JSON representation of what the Roles module looks like, which is found in the Community core module entry:

```
{
  "description": "A test set of commands for the community",
  "gateway_url": "http://127.0.0.1:8000/WaddleDBM/",
  "metadata": {
      "!community_set_role": {
        "action": "http://127.0.0.1:8000/WaddleDBM/community_members/set_role.json",
        "description": "Updates the roll of a given member in a community. The member updating the roll, must be the owner of the community, or have admin privilages. Example: !community update role [member_name_to_update_role] [name_of_the_role]",
        "method": "PUT",
        "parameters": [
          "community_name"
        ],
        "payload_keys": [
          "identity_name",
          "role_receiver",
          "role_name"
        ],
        "req_priv_list": [
          "admin"
        ]
      },
      "!community_get_role": {
        "action": "http://127.0.0.1:8000/WaddleDBM/community_roles/get_role_by_identity_and_community.json",
        "description": "Returns the role of the current user in the current community. Example: !community get role [my_community]",
        "method": "PUT",
        "parameters": [
        ],
        "payload_keys": [
          "identity_name",
          "community_name"
        ],
        "req_priv_list": [
          "read"
        ]
      }
    },
  "module_type_id": 1,
  "name": "Community"
}
```

## Module Commands

With the module entries discussed in the previous section, below is a list of commands as a brief summary of all the functions tha the roles module has to offer:

| Command | Description |
| --- | --- |
| !community set role | Updates the roll of a given member in a community. The member updating the roll, must be the owner of the community, or have admin privilages. Example: !community update role [member_name_to_update_role] [name_of_the_role] |
| !community get role | Returns the role of the current user in the current community. Example: !community get role [my_community] |


## Code Source files

The roles module consist of the collowing script files for all its functionality:

- [db.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/models/db.py) (Table declaration)
- [community_roles.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/controllers/community_roles.py)