# Always on PreBuilt In
All built in commands will start with a ! , while "marketplace" modules will start with a hashtag (#)
## Tag: Community <name>
### Specifics: 
* Manage <action> - Manages communities which you have access to! Common Actions:
  * add <name> - Creates a community if you are a premium user (counts against your community credits!)
  * rem <name> - Removes a community if you are the communities' owner
  * ls <optional pattern> - Basic search / listing of available communities (supports asterisks for wildcard)
  * desc <description> - Sets a description
* Attribute <action> - These are used to categorize or label communities using available options. Common actions:
  * add <name> - adds an attribute to the channel, common attributes are: LGBTQ+, Religious, Military, Women, Sports, Gaming, Competition, Music, LifeSkills (this encompases fitness, cooking, etc.) , and more!
  * ls <optional pattern> - Basic search / listing of available attributes (supports asterisks for wildcard)
  * rem <name> - Removes attribute
  * search <attribute> <optional pattern> - Lists all communities which have the attribute and match the pattern 
* Channel <action> <name> - Only allows this community to be used on specific channels, if this specific is never hit, communities are global! Common Actions: 
  * add - Adds a channel by name or ID (depending on platform support)
  * rem - Remove channel by name or ID (depending on platform support)
  * ls <optional pattern> - List all available channels in the community by name or ID (depending on platform support) (supports asterisks for wildcard)
* Currency <action> <name> - Manages currency for a user (or any for all). Common actions: 
  * add <amount> <name> - Adds currency to the user specified (or any for all)
  * active <amount> <name> <timeout> <pattern> - Adds currency to the user specified (or any for all) if they type something which matches the pattern within timeout (timeout is in seconds)
  * rem <amount> <name> - Removes currency from the user specified (or any for all)
  * give <amount> <name> - Takes from user who initiated workflow and gives to specified user
  * ls <optional pattern> - Specifies where on the scoreboard a user (or any for all) lands position wise!
  * raffle <amount> <mode> <timeout> - Allows users to enter into a raffle for currency, common modes are: single, multi, roulette and timeout is in seconds!
* Name <name> - Sets the name to the new specified name
* Prize <action> - Creates a prize for a raffle / giveaway!
  * add <name> <description> <cost> <timeout> - Adds a Prize for which the community can enter for a chance to get! Timeout is in seconds! 
  * rem <name> - Removes the prize without a winner
  * winner <name> [announce] - Closes the prize and sets the winner to user id / name specified and if announce afterwards, will announce in the channels within the community
  * active <name> <timeout> <pattern> [announce] - Sets the prize to claiming status and sets the winner to user id / name specified and if announce afterwards, will announce in the channels within the community, winner must claim the prize within timeout (timeout in seconds) by matching the pattern
  * ls <status> <optional pattern> - List available prizes within community (supports asterisks for wildcard). Statuses: Open, Claiming, Closed . If the status is Claiming, will state winner and amount of time remaining to claim
* Role <action> - The global community has the following roles for example: Premium (For premium SaaS users, Creator (a la streamer). Common Actions: 
  * ls <optional pattern> - gives a list of all community roles 
  * add <name> - creates a new role with specified name
  * rem  <name> - removes a role
* User <action> - Manages users within the community. Common actions:
  * ls <optional pattern> - gives a list of roles the user is assigned to
  * add <name> <role> - Adds the user to the role
  * rem <name> <role> - Removes the user from the role
* More to come!

## Tag: Identity <name>
### Specifics:
 * RepCheck - Bans, Timeouts, Censor Hits, Channels Modding, etc. turn into a reputation score... everyone starts at 0
 * Ban - Bans user from channel
 * RemBan - Removes ban from user specified
 * TimeOut <time>  - Times out user for specified time in seconds (must match platform options) for user specified
 * RemTime - Removes time out for the user specified
 * RoleAdd 
 * IDValidation - Utilizes a third party service to validate your identity... which boosts your reputation
 * Puzzle - Asks the user a question (math, basic science, ascii word id, etc.) which they must pass or loose reputation (bot defense)
 * Role <action> - Manages the access list for roles. Common actions:
   * add <name> - Adds the role to the allow list
   * rem <name> - Removes the role from the allow list
   * ls - List the allow list of roles
 
## Tag: Policy
### Specifics:
* ChatReq <role name> <req name> - Sets requirements for the role of users before they can chat. Only applies first matched role, global community is always last. Common requirement names:
  * time <time>- Amount of time the user in this role has to be in the channel before they can talk
  * follow <bool> - Is the user in this role a follower (twitch) or subscriber (youtube) etc. of the channel
  * backer <bool> - Is the user in this role providing monetary support to this channel
  * IDValidation <bool> - Has the user in this role went through the ID Validation
  * Reputation <score> - Has the user in this role met or surpassed the reputation score set?
  * Puzzle <puzzle name> - Give the user in this role a puzzle which they must pass before they can chat
* RoleReq <community name> <role name> - Sets what roles in what communities are allowed, for example a common global role is Creator (a la streamer)... you can allow or disallow. This can be used to just allow your community members to join the chat. Any users which do not match any of these (when set) will automatically be timed out continously at the max timeout for the platform.
* AutoShout <community name> <role name> <optional text> - Sends a shoutout message to the channel when a user belonging to a community and role starts chatting on the channel, some platforms will add additional details (such as last game played) as well, if available.
* ChatMsg
  * word <word match> - block on a word match with spaces before and after
  * string <regex match> - block on a boost regex match

## Tag: Alias
### Specifics:
* Link <name> <action> - a linker object. Common actions:
  * tag <name> <param> - Sets the tag and it's params for this linker (required before link object goes active)
  * specific <name> <param> - Sets the specific and it's params for this linker
  * desc <description> - Sets the description for this alias
  * ls <optional pattern> - List available aliases
Because of the simplicity of the core code, it runs lightweight!
