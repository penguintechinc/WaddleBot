# Calender Module

The WaddleBot calender module, allows users to add events to a community's calender. These events have start and end times, that are announced to channels when the events either start, or finish.

## Relavent Tables

The following list of tables are related to the calender module:

| Table Name | List of Fields | Description |
| --- | --- | --- |
| calendar | <ul><li>community_id</li><li>event_name</li><li>event_description</li><li>event_start</li><li>event_end</li><li>not_start_sent</li><li>not_end_sent</li></ul> | A module that allows identities to create events to a calender, per community. |

## Modules Table Entry

As stated in the [Modules Table Entry](https://github.com/PenguinCloud/WaddleBot-Core/blob/WaddleBot-Documentation/docs/core-modules/dbm_core_modules.md#modules-table-entry) in the DBM core modules documentation, each module requires an entry in the modules table for interaction to be possible with the listener. 

The following is a JSON representation of what the Calender module looks like:

```
{
    "description": "A list of commands to manage community Calenders.",
    "gateway_url": "http://127.0.0.1:8000/WaddleDBM/",
    "metadata": {
        "!calender_add": {
            "action": "http://127.0.0.1:8000/WaddleDBM/calender/create.json",
            "description": "This command adds a new event to the calender. Example: !calender add [event_name] [event_description] [event_start] [event_end]",
            "method": "POST",
            "parameters": [
                "community_name"
            ],
            "payload_keys": [
                "identity_name",
                "event_name",
                "event_description",
                "event_start",
                "event_end"
            ],
            "req_priv_list": [
                "read",
                "write",
                "admin"
            ]
        },
        "!calender_get_all": {
            "action": "http://127.0.0.1:8000/WaddleDBM/calender/get_by_community.json",
            "description": "This command gets all the events in the calender for the current community. Example: !calender get all. Optionally, you can pass a start and end date to get all events on that time frame. Example: !calender get all [start_date] [end_date]",
            "method": "GET",
            "parameters": [
                "community_name"
            ],
            "payload_keys": [

            ],
            "req_priv_list": [
                "read"
            ]
        },
        "!calender_update": {
            "action": "http://127.0.0.1:8000/WaddleDBM/calender/update_by_name.json",
            "description": "This command updates an event in the calender. Example: !calender update [event_name] [event_description] [event_start] [event_end]",
            "method": "PUT",
            "parameters": [
                "community_name"
            ],
            "payload_keys": [
                "event_name",
                "event_description",
                "event_start",
                "event_end"
            ],
            "req_priv_list": [
                "read",
                "write",
                "admin"
            ]
        },
        "!calender_delete": {
            "action": "http://127.0.0.1:8000/WaddleDBM/calender/delete_by_name.json",
            "description": "This command deletes an event from the calender. Example: !calender delete [event_name]",
            "method": "DELETE",
            "parameters": [
                "community_name"
            ],
            "payload_keys": [
                "event_name"
            ],
            "req_priv_list": [
                "read",
                "write",
                "admin"
            ]
        }
    },
    "module_type_id": 1,
    "name": "Calender"
}
```

## Module Commands

With the module entries discussed in the previous section, below is a list of commands as a brief summary of all the functions tha the calender module has to offer:

| Command | Description |
| --- | --- |
| !calender add | This command adds a new event to the calender. Example: !calender add [event_name] [event_description] [event_start] [event_end] |
| !calender get all | This command gets all the events in the calender for the current community. Example: !calender get all. Optionally, you can pass a start and end date to get all events on that time frame. Example: !calender get all [start_date] [end_date] |
| !calender update | This command updates an event in the calender. Example: !calender update [event_name] [event_description] [event_start] [event_end] |
| !calender delete | This command deletes an event from the calender. Example: !calender delete [event_name] |


## Code Source files

The calender module consist of the collowing script files for all its functionality:

- [db.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/models/db.py) (Table declaration)
- [calendar.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/controllers/calendar.py)