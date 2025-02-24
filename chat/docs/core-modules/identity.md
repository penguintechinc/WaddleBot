# Introduction

The identity module is responsible for creating and maintaining your user identity, access, and authorizations.
It will tie together data about users using available data.
Example: You have a slack account and a discord account with the same email, it will automatically tie them into the same identity.

# Roles

## Community Namespace Roles

- Administrator (2)
- Moderator (1)
- User (0)
- Custom Roles (A-Z)

## Global Namespace Roles
- Administrator (2) - Main administrators of the platform, can do anything and access anything (should be very limited amount of these)
- Moderators (1) - Can report users
- User (0) - Can use the system

Custom roles will allow you to be more granular on a per module level but also generally assign roles to folks with a different name for whatever reason.

# Identity Tie-Down Methods
- Emails
- IP Address
- Text patterns using NLP / AI
- Emoji usage
- Time of Day trends
- Linked data (if available) such as linked accounts in Steam, Discord, etc.

We also are considering integrating something like ID.Me


