# Sentinel Project # 
Sentinel is an open source, extendable, command line tool designed to gather, organize and interpret information in a game development environment.  Additionally, Sentinel provides easy to use tools for common tasks ranging from creating and deploying game client builds, running automated tests, automatically filing bugs to directly notify developers about best practices.

[SentinelUE4 Repo](https://github.com/BusMoneyGames/SentinelUE4)

## Prerequisits ##
### Windows ###
- Python 3.6 + 
- Pipenv

## Get Started ##
- Clone Sentinel to your workstation (*git clone* )
- Update submodules ( *git submodule update --init --recursive*)
- Generate the default environment (*pipenv run python .\Sentinel.py setup-default-environment*)
- Update the config file with the correct info( *engine_root_path and project_root_path are required and can be relative paths* )
- Compile all the blueprints in the level (pipenv run python .\Sentinel.py commands compile-blueprints)

If the blueprint compile runs then Sentinel is correctly setup.

## Project Structure ##

The root project is SentinelCLI which is the standard entrypoint to use the tool.  SentinelCLI then implements modules with different repsponsibility that follow this pattern

```
SentinelCLI
sentinel.py
- sentinel_vcs ( module ) 
-- vcscli.py ( cli interface )
- sentinel_ue4 ( module ) 
-- ue4cli.py ( cli interface )
- sentinel_aws ( module ) 
-- awscli.py ( cli interface )
```
