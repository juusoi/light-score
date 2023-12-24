# Serverless functions

ESPN API parsers that will be utilized with Google Serverless Functions

## ESPN API

All ESPN NFL endpoints are listed here: 
- <https://gist.github.com/nntrn/ee26cb2a0716de0947a0a4e9a157bc1c>
- <https://gist.github.com/nntrn/ee26cb2a0716de0947a0a4e9a157bc1c/cd7462cd365e516d7499b43f027db4b8b1a2d6c0> 

ESPN API integration is implemented in `src/espn_integration.py` 

## Standings

An ESPN API parser is implemented in `src/standings_parser.py`, which will be utilized in Google Serverless Functions.

ESPN API for standings <https://cdn.espn.com/core/nfl/standings?xhr=1>

The current standings information is available in the `response.content.standings.groups` field.

## Latest Games

TODO