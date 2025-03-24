# Communities Module

The WaddleBot Communities module allows users to create and manage communities for users to collaborate across multiple routes, platforms, channels, platforms etc, within the WaddleBot space. 

The communities module contain several submodules, namely:

- Roles
- Routes
- Modules

## Roles

Every community contains its own set of roles that determines the interaction level that each identity has with either the community in question, or with waddlebot as a whole. 

Upon the creation of a community, a set of default roles are created for the community in question. These roles are created according to the default roles set in [Waddlebot's Default Roles](https://github.com/PenguinCloud/WaddleBot-Core/blob/WaddleBot-Documentation/docs/core-modules/dbm_core_modules.md#db-initialization)

## Modules

Each community have free access to waddlebot's core modules, but not marketplace modules. These modules need to be installed through the marketplace module and can then only be accessed by identities that have their current active context set to the community in question, as well as have the required roles. The required rolls can be set in the "modules" table for each command listed in the "metadata".

## Routes

Identities can join communities and have singular "active" communities, known as contexts, that determines where user commands are executed, if the commands are community based. Identities are able to join multiple communities, but only a singular community is "active" at a time per identity and identities can freely move between communities through what is known as a "context".

Using functionality within the routes module, communities contain a collection of channels, servers etc, where movement and interaction is limited to. 

If say for instance, community A is bound to channels A and B, but community B is bound to channels B and C, identities active in channel A are unable to join community B.

## Relavent Tables

The following list of tables are related to the community module:

| Table Name | List of Fields | Description |
| --- | --- | --- |
| communities | <ul><li>community_name</li><li>community_description</li></ul> | This is the parent communities table that all other community related tables reference. Contains only basic information (for now) |
| community_members | <ul><li>community_id</li><li>identity_id</li><li>role_id</li></ul> | Is the main binding point between identities and roles. |
| roles | <ul><li>name</li><li>community_id</li><li>description</li><li>priv_list</li><li>requirements</li></ul> | Contains a list of all the roles that is available to a community. Determines module access. |
| currency | <ul><li>community_id</li><li>identity_id</li><li>amount</li></ul> | Stores currency values of each identity, per community |
| identity_labels | <ul><li>community_id</li><li>identity_id</li><li>label</li></ul> | Contains labels that are created, per identity, that is unique to each community |
| routing | <ul><li>channel</li><li>community_id</li><li>routing_gateway_ids</li><li>aliases</li></ul> | A table containing all the routing gateways that a community has access to. |
| context | <ul><li>identity_id</li><li>community_id</li><ul> | A table that keeps track of the current community context of each identity. Only one context can be created per identity |
| calendar | <ul><li>community_id</li><li>event_name</li><li>event_description</li><li>event_start</li><li>event_end</li><li>not_start_sent</li><li>not_end_sent</li></ul> | A module that allows identities to create events to a calender, per community. |
| admin_contexts | <ul><li>identity_id</li><li>community_id</li><li>session_token</li><li>session_expires</li></ul> | Keeps track of administrator sessions that community admins need to sign into to access "admin" level commands of a community. |
| text_responses | <ul><li>community_id</li><li>text_val</li><li>response_val</li></ul> | Allows for the creation of text responses that the bot displays when a certain text command is inputted by a user |
| prizes | <ul><li>community_id</li><li>prize_guid</li><li>prize_name</li><li>prize_description</li><li>winner_identity_id</li><li>prize_status</li><li>timeout</li></ul> | Responsible for storing data related to giveaways that are hosted per community |
| alias_commands | <ul><li>community_id</li><li>alias_val</li><li>command_val</li></ul> | This module allows identities to create aliases for commands on a per community basis. |

## Modules Table Entry

As stated in the [Modules Table Entry](https://github.com/PenguinCloud/WaddleBot-Core/blob/WaddleBot-Documentation/docs/core-modules/dbm_core_modules.md#modules-table-entry) in the DBM core modules documentation, each module requires an entry in the modules table for interaction to be possible with the listener. 

The following is a JSON representation of what the Communities module looks like:

```
{
  "description": "A test set of commands for the community",
  "gateway_url": "http://127.0.0.1:8000/WaddleDBM/",
  "metadata": {
    "!community_join": {
      "action": "http://127.0.0.1:8000/WaddleDBM/community_members/create_member.json",
      "description": "Creates a new member for a given community. Example: !community join [my_community]",
      "method": "POST",
      "parameters": [],
      "payload_keys": [
        "community_name",
        "identity_name"
      ],
      "req_priv_list": []
    },
    "!community_leave": {
      "action": "http://127.0.0.1:8000/WaddleDBM/community_members/remove_member.json",
      "description": "Leaves the given community. Example: !community leave [my_community]",
      "method": "DELETE",
      "parameters": [],
      "payload_keys": [
        "community_name",
        "identity_name"
      ],
      "req_priv_list": []
    },
    "!community_manage_add": {
      "action": "http://127.0.0.1:8000/WaddleDBM/communities/create_by_name.json",
      "description": "Add a new community. Example: !community manage add [my_community]",
      "method": "POST",
      "parameters": [],
      "payload_keys": [
        "identity_name",
        "community_name"
      ],
      "req_priv_list": []
    },
    "!community_manage_desc": {
      "action": "http://127.0.0.1:8000/WaddleDBM/communities/update_desc_by_name.json",
      "description": "Add a description to a community. Example: !community manage desc [My community description] <my_community>",
      "method": "PUT",
      "parameters": [
        {
          "description": "The name of the community",
          "name": "community_name",
          "required": true
        }
      ],
      "payload_keys": [
        "identity_name",
        "community_description"
      ],
      "req_priv_list": [
        "write",
        "admin"
      ]
    },
    "!community_manage_ls": {
      "action": "http://127.0.0.1:8000/WaddleDBM/communities/get_all.json",
      "description": "List all the communities. Example: !community manage ls",
      "method": "GET",
      "parameters": [],
      "payload_keys": [],
      "req_priv_list": []
    },
    "!community_manage_rem": {
      "action": "http://127.0.0.1:8000/WaddleDBM/communities/delete_by_name.json",
      "description": "Remove a community. Example: !community manage rem <my_community>",
      "method": "DELETE",
      "parameters": [],
      "payload_keys": [
        "identity_name",
        "community_name"
      ],
      "req_priv_list": [
        "admin",
        "delete"
      ]
    },
    "!community_members_ls": {
      "action": "http://127.0.0.1:8000/WaddleDBM/community_members/get_names_by_community_name.json",
      "description": "Returns a list of all the members of the current community. Example: !community members ls",
      "method": "GET",
      "parameters": [
        "community_name"
      ],
      "payload_keys": [],
      "req_priv_list": [
        "read"
      ]
    },
    "!community_update_role": {
      "action": "http://127.0.0.1:8000/WaddleDBM/community_members/update_member_role.json",
      "description": "Updates the roll of a given member in a community. The member updating the roll, must be the owner of the community. Example: !community update role[member_name_to_update_role] [name_of_the_role]",
      "method": "PUT",
      "parameters": [
        "community_name"
      ],
      "payload_keys": [
        "identity_name",
        "member_name",
        "role_name"
      ],
      "req_priv_list": [
        "admin"
      ]
    }
  },
  "module_type_id": 1,
  "name": "Community"
}
```

Another module entry that is important to communities, specifically the installation of modules into a community, is the following:

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

With the module entries discussed in the previous section, below is a list of commands as a brief summary of all the functions tha the community module has to offer:

| Command | Description |
| --- | --- |
| !community join | Creates a new member for a given community. Example: !community join [my_community] |
| !community leave | Leaves the given community. Example: !community leave [my_community] |
| !community manage add | Add a new community. Example: !community manage add [my_community] |
| !community manage desc | Add a description to a community. Example: !community manage desc [My community description] <my_community> |
| !community manage ls | List all the communities. Example: !community manage ls |
| !community manage rem | Remove a community. Example: !community manage rem <my_community> |
| !community members ls | Returns a list of all the members of the current community. Example: !community members ls |
| !community update roll | Updates the roll of a given member in a community. The member updating the roll, must be the owner of the community. Example: !community update role[member_name_to_update_role] [name_of_the_role] |
| !marketplace install | This command installs a marketplace module into the given community. Example: !marketplace install <my_community> [module_id] |
| !marketplace uninstall | This command uninstalls a module from a community. Example: !marketplace install <my_community> [module_id] |

## Code Source files

The communities module consist of the collowing script files for all its functionality:

- [db.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/models/db.py) (Table declaration)
- [communities.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/controllers/communities.py)
- [community_members.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/controllers/community_members.py)
- [community_modules.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/controllers/community_modules.py)
- [community_roles.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/controllers/community_roles.py)