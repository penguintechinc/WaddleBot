# Identity Label Module

The WaddleBot identity label module keeps track of all labels that have been assigned to identities on a community based level.

## Relavent Tables

The following list of tables are related to the identity label module:

| Table Name | List of Fields | Description |
| --- | --- | --- |
| identity_labels | <ul><li>community_id</li><li>identity_id</li><li>label</li></ul> | Contains labels that are created, per identity, that is unique to each community |

## Modules Table Entry

As stated in the [Modules Table Entry](https://github.com/PenguinCloud/WaddleBot-Core/blob/WaddleBot-Documentation/docs/core-modules/dbm_core_modules.md#modules-table-entry) in the DBM core modules documentation, each module requires an entry in the modules table for interaction to be possible with the listener. 

The following is a JSON representation of what the Identity Label module looks like:

```
{
  "description": "A list of commands to manage identity labels.",
  "gateway_url": "http://127.0.0.1:8000/WaddleDBM/",
  "metadata": {
      "!identity_label_get": {
          "action": "http://127.0.0.1:8000/WaddleDBM/identity_label/get_by_identity_and_community.json",
          "description": "This command gets the identity label for the current user. Example: !identity label get",
          "method": "GET",
          "parameters": [
              "community_name"
          ],
          "payload_keys": [
              "identity_name"
          ],
          "req_priv_list": [
              "read"
          ]
      },
      "!identity_label_add": {
          "action": "http://127.0.0.1:8000/WaddleDBM/identity_label/create.json",
          "description": "This command adds a new identity label to the current user. Example: !identity label add [label]",
          "method": "POST",
          "parameters": [
              "community_name"
          ],
          "payload_keys": [
              "identity_name",
              "label"
          ],
          "req_priv_list": [
              "read",
              "write",
              "admin"
          ]
      },
      "!identity_label_update": {
          "action": "http://127.0.0.1:8000/WaddleDBM/identity_label/update_by_identity_and_community.json",
          "description": "This command updates an identity label for the current user. Example: !identity label update [label]",
          "method": "PUT",
          "parameters": [
              "community_name"
          ],
          "payload_keys": [
              "identity_name",
              "label"
          ],
          "req_priv_list": [
              "read",
              "write",
              "admin"
          ]
      },
      "!idenity_label_delete": {
          "action": "http://127.0.0.1:8000/WaddleDBM/identity_label/delete_by_identity_and_community.json",
          "description": "This command deletes an identity label for the current user. Example: !identity label delete",
          "method": "DELETE",
          "parameters": [
              "community_name"
          ],
          "payload_keys": [
              "identity_name"
          ],
          "req_priv_list": [
              "read",
              "write",
              "admin"
          ]
      }
  },
  "module_type_id": 1,
  "name": "Identity Label"
}
```

## Module Commands

With the module entries discussed in the previous section, below is a list of commands as a brief summary of all the functions tha the identity label module has to offer:

| Command | Description |
| --- | --- |
| !identity_label_get | This command gets the identity label for the current user. Example: !identity label get |
| !identity_label_add | This command adds a new identity label to the current user. Example: !identity label add [label] |
| !identity_label_update | This command updates an identity label for the current user. Example: !identity label update [label] |
| !idenity_label_delete | This command deletes an identity label for the current user. Example: !identity label delete | 

## Code Source files

The identity label module consist of the collowing script files for all its functionality:

- [db.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/models/db.py) (Table declaration)
- [identity_label.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/controllers/identity_label.py)