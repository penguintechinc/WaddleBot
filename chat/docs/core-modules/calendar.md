# Introduction
This module creates a database which is a "Source of Truth" for calendars.
It stores data about the event and pushes it to any connected interfaces with the correct routing.

# Data Fields
- Crontab (datetime / repeat)
- Length (Float / Hours with 1 decimel)
- POC (Email)
- More Info (URL)
- Banner (URL)
- Description
- Location (URL) - This should be a link to google map or a virtual bridge invite or discord channel invite

Data fields are pushed and pulled based on available fields on the platform or specified in the command

Command Example:

``` !calendar add Cron:"0 0 6 6 9 ? 2025" Length:"2.5" POC:"info@barcitizen.org" Info:"https://ptg.best/eventXYZ" Banner:"https://penguintech.io/images/banner.jpg" Description:"We will meet at the back of the bar under the rainbow!" Location:"https://maps.google.com/somelocation" ```