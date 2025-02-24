# Text Response Module

The WaddleBot Text response module, allows identities in a community to map a text response value to a given text value. This is on a per community basis and text responses outside a given community cannot be used.

## Relavent Tables

The following list of tables are related to the Text Response module:

| Table Name | List of Fields | Description |
| --- | --- | --- |
| text_responses | <ul><li>community_id</li><li>text_val</li><li>response_val</li></ul> | Allows for the creation of text responses that the bot displays when a certain text command is inputted by a user |

## Modules Table Entry

As stated in the [Modules Table Entry](https://github.com/PenguinCloud/WaddleBot-Core/blob/WaddleBot-Documentation/docs/core-modules/dbm_core_modules.md#modules-table-entry) in the DBM core modules documentation, each module requires an entry in the modules table for interaction to be possible with the listener. 

The following is a JSON representation of what the Text Response module looks like:

```
{
  "description": "A list of commands to manage text responses.",
  "gateway_url": "http://127.0.0.1:8000/WaddleDBM/",
  "metadata": {
    "!text": {
      "action": "http://127.0.0.1:8000/WaddleDBM/text_responses/get_by_text.json",
      "description": "This command gets a text response from a given value. Example: !text [text]",
      "method": "GET",
      "parameters": [
        "community_name"
      ],
      "payload_keys": [
        "text"
      ],
      "req_priv_list": []
    },
    "!text_delete": {
      "action": "http://127.0.0.1:8000/WaddleDBM/text_responses/delete_by_text.json",
      "description": "This command delete a text response from a given value. Example: !text delete [text]",
      "method": "DELETE",
      "parameters": [
        "community_name"
      ],
      "payload_keys": [
        "text"
      ],
      "req_priv_list": []
    },
    "!text_get_all": {
      "action": "http://127.0.0.1:8000/WaddleDBM/text_responses/get_all.json",
      "description": "This command gets all the text responses for the current community.",
      "method": "GET",
      "parameters": [
        "community_name"
      ],
      "payload_keys": [],
      "req_priv_list": []
    },
    "!text_set": {
      "action": "http://127.0.0.1:8000/WaddleDBM/text_responses/set_text_response.json",
      "description": "This command maps a text response to a text value. Example: !text set [text_to_bind_response_to] [response]",
      "method": "POST",
      "parameters": [
        "community_name"
      ],
      "payload_keys": [
        "text",
        "response"
      ],
      "req_priv_list": []
    }
  },
  "module_type_id": 1,
  "name": "Text Response"
}
```

## Module Commands

With the module entries discussed in the previous section, below is a list of commands as a brief summary of all the functions tha the text response module has to offer:

| Command | Description |
| --- | --- |
| !text | This command gets a text response from a given value. Example: !text [text] |
| !text delete | This command delete a text response from a given value. Example: !text delete [text] |
| !text get all | This command gets all the text responses for the current community. |
| !text set | This command maps a text response to a text value. Example: !text set [text_to_bind_response_to] [response] |

## Code Source files

The text response module consist of the collowing script files for all its functionality:

- [db.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/models/db.py) (Table declaration)
- [text_responses.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/controllers/text_responses.py)