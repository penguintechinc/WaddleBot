# Introduction
 The reputation module is what kicked off the idea for this bot alongside of namespaces. 
 Based on your interactions which the bot monitors, you may or may not be able to do certain actions or you may be autobanned.

# Scoring
- 300-850 (FICO)
- All identities Start at 600
* "alias groups" similiar to FICO: Bad, fair, good, excellent

## Adjustments
- General interaction adds to your score a little
- Joining riskier interactions (such as raffles / giveaways) takes a little away from your reputation
- Getting timed out or banned will significantly decrease your score, but not enough that you will fall into bad on a single one

## Scoping
- All reputation adjustments happen within your communities active on the sub-interface
- All reputation adjustments happen on the global namespace as well

## Bouncer
- Community Namespace Administrators will be able to set reputation requirements if they wish, if not set it is assumed off, example:

```
---
policy:
  minRep: 600
  enforceMethod: TimeOut # Can also be Ban
  minDays: 1
  minHours: 0 # These are additive
  linkLevel: 1 # Role level 
```