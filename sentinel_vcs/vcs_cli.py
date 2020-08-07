import logging
import pathlib
from pprint import pprint
import click
import json
from Vcs import GitComponent

def _read_config(path):
    """Reads the assembled config"""

    if path.exists():
        f = open(path, "r")
        config = json.load(f)
        f.close()

        return config
    else:
        print(f"No config found at {path}")
        print("Exiting!")
        quit(1)


def get_config_path(ctx):
    """Construct the config dict path"""
    return pathlib.Path(ctx.obj['PROJECT_ROOT']).joinpath("_generated_sentinel_config.json")


def get_config(ctx):
    """Return the environment config dict"""
    return _read_config(get_config_path(ctx))

def get_git_info_object(ctx, commit_id=""):
    """return the commit id based on the config"""

    config = get_config(ctx)
    git_info = GitComponent.GitInfo(config, commit_id=commit_id)

    return git_info

@click.group()
@click.option('--project_root', default="", help="Path to the config overwrite folder")
@click.option('--output', type=click.Choice(['text', 'json']), default='text', help="Output type.")
@click.option('--no_version', type=click.Choice(['true', 'false']), default='true', help="Skips output version")
@click.option('--debug', type=click.Choice(['true', 'false']), default='false', help="Verbose logging")
@click.pass_context
def cli(ctx, project_root, output, no_version, debug):
    """Sentinel Unreal Component handles running commands interacting with unreal engine"""
    ctx.ensure_object(dict)
    ctx.obj['PROJECT_ROOT'] = project_root

@cli.command()
@click.option('-o', '--output', type=click.Choice(['text', 'json']), default='text', help="Output type.")
@click.option('--commit', default="", help="Commit ID, return current if not specified")
@click.pass_context
def get_commit_details(ctx, output, commit):
    """Return information about the commit"""
    
    info = get_git_info_object(ctx, commit)
    
    commit_info = info.get_info_from_commit()

    if output == 'json':
        print(json.dumps(commit_info, indent=4))
    elif output == 'text':
        print("")

@cli.command()
@click.option('-o', '--output', type=click.Choice(['text', 'json']), default='text', help="Output type.")
@click.pass_context
def list_submodules(ctx, output):
    """Return a list of submodules in project"""

    submodules = GitComponent.list_submodules(get_config(ctx))

    if output == 'json':
        print(json.dumps(submodules, indent=4))
    elif output == 'text':
        print(submodules)

@cli.command()
@click.option('--short', is_flag=True, help="return as short commit")
@click.option('-o', '--output', type=click.Choice(['text', 'json']), default='text', help="Output type.")
@click.pass_context
def get_current_commit_id(ctx, short, output):
    """Returns the current commit ID"""
    info = get_git_info_object(ctx)
    
    if short:
        commit_id = info.short_commit_id
    else:
        commit_id = info.commit_id

    if output == 'json':
        print(json.dumps({"commitID":commit_id}, indent=4))
    elif output == 'text':
        print(commit_id)


if __name__ == "__main__":
    cli()
