# Flow
Message Received -> Tags -> Specifics -> Run Action Script

## Tags
Each chat message is evaluated against a tag, which are general types or classes or modules. The most basic three are Command, Event and Chat.
Commands look for an ! , events looks for key notifications from the platform (such as trains, subscription, etc. on Twitch), and finally the chat tag does string matches for specifics on chats... keep these at a minimal as they are the most resource intensive!
Behind the scenes, each tag is a python3.11 class! Some tags support parameters afterwards, while some dont. See documentation for Tags.

## Specifics
The specifics are the actual modules of the tag class. These are either pre-built into the tag class which are there from the start, or optional installed from either the store or locally. Common modules installed fall into core project extension modules, or community modules!
Specifics are essentially a function (though they may utilize sub-functions) and may take or require a parameter. See documentation for specifics.

# Examples

## Tag: Command
### Specific: 
* !help - List how to use the command tag

## Tag: Event
### Specifc: 
* TwitchSub - Actions to take when a subscriber to twitch happens

## Tag: StringSearch
### Specifics: 
* Racist or Unwanted Word - matches on word and takes an action
