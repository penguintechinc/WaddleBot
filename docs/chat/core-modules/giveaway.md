# Giveaway Module

The WaddleBot giveaway module allows users start giveways in specific communities that identities in the given communities can join for a prize. The winner can either be set by the person who created the giveaway, or selected randomly. Giveaways can be allocated a timeout value that will then automatically close the giveway after a certain time. 

## Relavent Tables

The following list of tables are related to the giveaway module:

| Table Name | List of Fields | Description |
| --- | --- | --- |
| prizes | <ul><li>community_id</li><li>prize_guid</li><li>prize_name</li><li>prize_description</li><li>winner_identity_id</li><li>prize_status</li><li>timeout</li></ul> | The prizes table keeps track of community based giveaways with all the necessary prize info, as well as unique GUID's that identities can join on. |
| prize_statuses | <ul><li>status_name</li><li>description</li></ul> | This table keeps track of the different possible status types in the giveaway module. |
| prize_entries | <ul><li>prize_id</li><li>identity_id</li></ul> | This table keeps track of all the identities that have entered a given giveaway, via a prize ID |

## Modules Table Entry

As stated in the [Modules Table Entry](https://github.com/PenguinCloud/WaddleBot-Core/blob/WaddleBot-Documentation/docs/core-modules/dbm_core_modules.md#modules-table-entry) in the DBM core modules documentation, each module requires an entry in the modules table for interaction to be possible with the listener. 

The following is a JSON representation of what the giveaway module looks like:

```
{
  "description": "A list of commands to manage giveaways.",
  "gateway_url": "http://127.0.0.1:8000/WaddleDBM/",
  "metadata": {
      "!giveaway_create": {
          "action": "http://127.0.0.1:8000/WaddleDBM/giveaway/create.json",
          "description": "This command creates a giveaway for the current community. Example: !giveaway create [prize_name] [prize_description] [timeout]",
          "method": "GET",
          "parameters": [
              
          ],
          "payload_keys": [
              "community_name",
              "identity_name",
              "prize_name",
              "prize_description",
              "timeout"
          ],
          "req_priv_list": [
              "admin",
              "write",
              "read"
          ]
      },
      "!giveaway_get_all": {
          "action": "http://127.0.0.1:8000/WaddleDBM/giveaway/get_all_by_community_name.json",
          "description": "This command fetches all the giveaways for the current community. Example: !giveaway get all",
          "method": "GET",
          "parameters": [
          ],
          "payload_keys": [
              "community_name"
          ],
          "req_priv_list": [
              "read"
          ]
      },
      "!giveaway_enter": {
          "action": "http://127.0.0.1:8000/WaddleDBM/giveaway/enter.json",
          "description": "This command allows the current identity to enter a given giveaway through a given giveaway GUID. Example: !giveaway enter [giveaway_guid]",
          "method": "GET",
          "parameters": [
          ],
          "payload_keys": [
              "community_name",
              "identity_name",
              "guid"
          ],
          "req_priv_list": [
              "read"
          ]
      },
      "!giveaway_get_entries": {
          "action": "http://127.0.0.1:8000/WaddleDBM/giveaway/get_entries.json",
          "description": "This command retrieves all the entries for a given giveaway. Example: !giveaway get entries [giveaway_guid]",
          "method": "GET",
          "parameters": [
          ],
          "payload_keys": [
              "guid"
          ],
          "req_priv_list": [
              "read"
          ]
      },
      "!giveaway_close_with_winner": {
          "action": "http://127.0.0.1:8000/WaddleDBM/giveaway/close_with_winner.json",
          "description": "This command closes a giveaway and selects a winner. Example: !giveaway close with winner [giveaway_guid] [winner_name]",
          "method": "GET",
          "parameters": [
          ],
          "payload_keys": [
              "guid",
              "winner_identity_name"
          ],
          "req_priv_list": [
              "read",
              "write",
              "admin"
          ]
      }
  },
  "module_type_id": 1,
  "name": "Giveaway"
}
```

## Module Commands

With the module entries discussed in the previous section, below is a list of commands as a brief summary of all the functions tha the community module has to offer:

| Command | Description |
| --- | --- |
| !giveaway create | This command creates a giveaway for the current community. Example: !giveaway create [prize_name] [prize_description] [timeout] |
| !giveaway get all | This command fetches all the giveaways for the current community. Example: !giveaway get all |
| !giveaway enter | This command allows the current identity to enter a given giveaway through a given giveaway GUID. Example: !giveaway enter [giveaway_guid] |
| !giveaway get entries | This command retrieves all the entries for a given giveaway. Example: !giveaway get entries [giveaway_guid] |
| !giveaway close with winner | This command closes a giveaway and selects a winner. Example: !giveaway close with winner [giveaway_guid] [winner_name] |

## Code Source files

The communities module consist of the collowing script files for all its functionality:

- [db.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/models/db.py) (Table declaration)
- [giveaway.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/controllers/giveaway.py)