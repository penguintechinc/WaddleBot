# Currency Module

The WaddleBot currency module allows a currency to be allocated to identities of individual communities. When an identity joins a community, that identity is allocated a default amount of currency and can gain currency through different means, such as by giving currency away, through giveaways, through raffles, or through duels.

## Relavent Tables

The following list of tables are related to the currency module:

| Table Name | List of Fields | Description |
| --- | --- | --- |
| currency | <ul><li>community_id</li><li>identity_id</li><li>amount</li></ul> | Stores currency values of each identity, per community |

## Modules Table Entry

As stated in the [Modules Table Entry](https://github.com/PenguinCloud/WaddleBot-Core/blob/WaddleBot-Documentation/docs/core-modules/dbm_core_modules.md#modules-table-entry) in the DBM core modules documentation, each module requires an entry in the modules table for interaction to be possible with the listener. 

The following is a JSON representation of what the currency module looks like:

```
{
  "description": "A list of commands to manage currencies for users within communities.",
  "gateway_url": "http://127.0.0.1:8000/WaddleDBM/",
  "metadata": {
    "!currency_add": {
      "action": "http://127.0.0.1:8000/WaddleDBM/currency/add_currency.json",
      "description": "This command adds a given amount of currency to the current user. Example: !currency add [amount]",
      "method": "POST",
      "parameters": [
        "community_name"
      ],
      "payload_keys": [
        "identity_name",
        "amount"
      ],
      "req_priv_list": [
        "read",
        "write",
        "admin"
      ]
    },
    "!currency_get": {
      "action": "http://127.0.0.1:8000/WaddleDBM/currency/get_currency.json",
      "description": "This command gets the currency of the current user. Example: !currency get",
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
    "!currency_give": {
      "action": "http://127.0.0.1:8000/WaddleDBM/currency/transfer_currency.json",
      "description": "This command gives currency from one user to another. Example: !currency give [user] [amount]",
      "method": "POST",
      "parameters": [
        "community_name"
      ],
      "payload_keys": [
        "identity_name",
        "receiver_name",
        "amount"
      ],
      "req_priv_list": [
        "read",
        "write"
      ]
    },
    "!currency_rem": {
      "action": "http://127.0.0.1:8000/WaddleDBM/currency/subtract_currency.json",
      "description": "This command removes a given amount of currency to the current user. Example: !currency rem [amount]",
      "method": "POST",
      "parameters": [
        "community_name"
      ],
      "payload_keys": [
        "identity_name",
        "amount"
      ],
      "req_priv_list": [
        "read",
        "write"
      ]
    }
  },
  "module_type_id": 1,
  "name": "Currency"
}
```

## Module Commands

With the module entries discussed in the previous section, below is a list of commands as a brief summary of all the functions tha the community module has to offer:

| Command | Description |
| --- | --- |
| !currency_add | This command adds a given amount of currency to the current user. Example: !currency add [amount] |
| !currency_get | This command gets the currency of the current user. Example: !currency get |
| !currency_give | This command gives currency from one user to another. Example: !currency give [user] [amount] |
| !currency_rem | This command removes a given amount of currency to the current user. Example: !currency rem [amount] |

## Code Source files

The communities module consist of the collowing script files for all its functionality:

- [db.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/models/db.py) (Table declaration)
- [currency.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/controllers/currency.py)