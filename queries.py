import click
import utilities
import json


@click.group()
@click.option('--project_root', default="", help="Path to the config overwrite folder")
@click.option('--output', type=click.Choice(['text', 'json']), default='text', help="Output type.")
@click.option('--no_version', type=click.Choice(['true', 'false']), default='true', help="Skips output version")
@click.option('--debug', type=click.Choice(['true', 'false']), default='false', help="Verbose logging")
@click.pass_context
def cli(ctx, project_root, output, debug, no_version):
    """Sentinel Commands"""
    ctx = utilities.convert_parameters_to_ctx(ctx, project_root=project_root, output=output,
                                              debug=debug, no_version=no_version)

@cli.command()
@click.pass_context
def get_commit_id(ctx):
    """Returns the current commit ID"""

    global_args = utilities.convert_input_to_dict(ctx)
    cmd = utilities.get_commandline("./Sentinel.py ", ["run-module", "vcs", "get-current-commit-id"])
    utilities.run_cmd(cmd)

if __name__ == "__main__":
    cli()
