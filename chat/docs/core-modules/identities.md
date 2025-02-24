# Identities Module

The WaddleBot Identities module is responsible for managing the storage of any users that are currently part of waddlebot. Any user that interacts with waddlebot in any way, must be added to the identities module before they can interact with any other module.

## Identity Onboarding Process

To add an identity to waddlebot, no command input is required from the user's side. A user simply needs to send a text chat to any channel that is bound to Waddlebot from any signal type, for instance a chat channel on Twitch that is bound to waddlebot. Waddlebot can then use the identity in multiple other bound modules. 

## Identities' most important modules

Even though there are multiple modules that require identity information, the following modules are the most important ones for the main identity interactions:

- Communities
- Identity Roles
- Context

### Communities

For identities to interact with waddlebot communities, they must first join a given community through any channel that is bound to waddlebot, using the following command:

`!community join [community name here]`

### Identity Roles

Each identity in a community have a specific role. This determines a user's interaction with the community and it's modules.

Currently, the following roles are available on waddlebot be default:

- Owner
- Administrator
- Moderator
- Member

Identities that newly join a community with the previous section's command, are given the "Member" role by default. Owners and administrators can change a user's role. Owner's are only allocated to identities that have created a new community. A role can be set by an administrator, by using the following command:

`!`

### Context

Identities have active "Contexts", that determine what is currently their active community. What this means, is that if an identity has an active context of of Community A, all their interactions through commands that are related to a community, are only going to have an effect on community A and no others, if the command is a community based command. 

To change between contexts, use the following command:

`!namespace switch [community name]`

## Relavent Tables

The following list of tables are related to the community module:

| Table Name | List of Fields | Description |
| --- | --- | --- |
| identities | <ul><li>name</li><li>country</li><li>ip_address</li><li>browser_fingerprints</li><li>reputation</li></ul> | This table stores all identities that interact with waddlebot in any way |
| identity_labels | <ul><li>community_id</li><li>identity_id</li><li>label</li></ul> | Contains labels that are created, per identity, that is unique to each community |
| community_members | <ul><li>community_id</li><li>identity_id</li><li>role_id</li></ul> | Table that binds identities to different communities |
| reputation | <ul><li>community_id</li><li>identity_id</li><li>amount</li></ul> | Table that keeps track of individual identity reputation amounts, per community. |
| currency | <ul><li>community_id</li><li>identity_id</li><li>amount</li></ul> | This keeps track of individual currency amounts of each identity, per community. |
| context | <ul><li>identity_id</li><li>community_id</li><ul> | A table that keeps track of the current community context of each identity. Only one context can be created per identity |
| admin_contexts | <ul><li>identity_id</li><li>community_id</li><li>session_token</li><li>session_expires</li></ul> | Keeps track of administrator sessions that community admins need to sign into to access "admin" level commands of a community. |
| prizes | <ul><li>community_id</li><li>prize_guid</li><li>prize_name</li><li>prize_description</li><li>winner_identity_id</li><li>prize_status</li><li>timeout</li></ul> | Responsible for storing data related to giveaways that are hosted per community |
| prize_entries | <ul><li>prize_id</li><li>identity_id</li></ul> | This table keeps track of all the identities that have entered a given giveaway, via a prize ID |

## Modules Table Entry

As stated in the [Modules Table Entry](https://github.com/PenguinCloud/WaddleBot-Core/blob/WaddleBot-Documentation/docs/core-modules/dbm_core_modules.md#modules-table-entry) in the DBM core modules documentation, each module requires an entry in the modules table for interaction to be possible with the listener. 

However, the identity module does not currently have any direct commands, but do have related commands found in the identity label module.

Main interactions between the listener and the identities module pop off automatically.

## Code Source files

The communities module consist of the collowing script files for all its functionality:

- [db.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/models/db.py) (Table declaration)
- [identities.py](https://github.com/PenguinCloud/WaddleDBM/blob/1.1.0-test/controllers/identities.py)