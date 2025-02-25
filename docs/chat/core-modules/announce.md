# Introduction

This module is responsible for announcements to the channel.
It is referenced by almost all other modules which want to kick back a response


# Types

## Ticker
This is a browser source meant to be on the bottom of a stream. It will scroll text from right to left similar to news stations do.

## Window
This is a browser source for media which acts as a sort of overlay

## StdOut
This is typically a text channel which it can push messages to

## DM
This is a text output but in a private message format, hitting up the user's DMs

## Private
This is a text output which will push to "only visible to you" if available on the platform, otherwise will fall back to DMs

# Triggers

# Scheduled (Cron)
Utilizes CronTab to time a message once or on repeat

# Command
Receives a command from chat

# Event
This is either a calendar or channel event (ie: Sub / Follow / Money Event)