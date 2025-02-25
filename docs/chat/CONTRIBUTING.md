SDK info and onboarding process here @thysw95

# WaddleBot Module Protocol Definition
sent via webhook to AWS Lambda:
* event
* amount
* userid
* text
* namespace
* platform / interface / subinterface 

``` {"event": "subscription", "amount": "5.00", "userid": "PenguinzPlays", "Text": "I love to support!" , "Namespace": "ProWaddlers", "Resource": { "Platform": "Twitch", "Interface": "None", "Sub-Interface": "PenguinzPlays"}}```

 
receive via webhook:
* msg: text
* media: url to media (gif, video, sound, etc.) 
* stdout: (chat, dm, ticker, browser)
* platform / interface / subinterface 
