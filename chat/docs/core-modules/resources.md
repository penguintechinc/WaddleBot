# Introductions

Our resource manager is what connects to the "sources". 
Example resource - Twitch Channel or Discord Channel

We heavily use Linux networking terms as our team and founder are heavily into the Linux realm.

# Terminology

- Resource: Any place which data is streamed from, such as a text channel
- Platform: Resource's platform type/name, such as Twitch or Discord
- Interface: The server or instance of the platform for the resource
- SubInterface: The channel or stream itself
- Routes: Definitions of what data to send from one resource to another 
- Community Namespaces: Similiar to linux namespaces, restricts data to confine element, such as a stream team or server
- Routers: similiar to router in networking, these data
- Broadcast: Resource routes which are set to mode of broadcast, which means it will send the data to all connected resources to the router


# Community Namespace

## Adding Resources 

1. Resource owner adds Waddlebot to their server / channel
2. Community Administrator adds an interface to the router, such as PenguinTech's Discord Server - ```!community invite discord penguinzplays```
2. Resource owner accepts the invite - ```!community join CoolCommunity```


# Routes

## Rules

You can specify what should and shouldnt be passed through. By default any resources not specified as True are assumed false.

```
---
source:
  platform: twitch
  interface: none
  subinterface: penguinzplays
destination:
  platform: discord
  interface: penguinzplays
  subinterface: general
resources:
  text: True
  events: False
  roles:
    administrator: False
    moderator: True
    User: True
    Other: True
  announcements: False
```


## Resources

- text: any text or emotes on the source subinterface
- events: any calendar event
- roles: any roles, including the admin, moderator, user, and any custom ones (where the platform supports it)
- announcements: Any announcements by the platform (subs, etc.) or administrators such as ``` !community announce add Discord PenguinzPlays news-announce ```
- badges: these wont be in the initial release but are community defined and awarded badges for accomplishments
