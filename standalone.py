import click
import pathlib
import utilities
import logging

root_folder = pathlib.Path(__file__).parent
SENTINEL_ENVIRONMENT = str(root_folder.joinpath("SentinelEnvironment/SentinelEnvironment.py"))
SENTINEL_UE4 = str(root_folder.joinpath("SentinelUE4/SentinelUE4.py "))
SENTINEL_COMMANDS = str(root_folder.joinpath("commands.py"))


@click.group()
@click.option('--project_root', default="", help="Path to the config overwrite folder")
@click.option('--output', type=click.Choice(['text', 'json']), default='text', help="Output type.")
@click.option('--no_version', type=click.Choice(['true', 'false']), default='true', help="Skips output version")
@click.option('--debug', type=click.Choice(['true', 'false']), default='false',  help="Verbose logging")
@click.pass_context
def cli(ctx, project_root, output, debug, no_version):
    """Sentinel Unreal Component handles running commands interacting with unreal engine"""

    if debug == 'true':
        L.setLevel(logging.DEBUG)

    ctx = utilities.convert_parameters_to_ctx(ctx, project_root=project_root, output=output,
                                              debug=debug, no_version=no_version)


@cli.command(context_settings=dict(ignore_unknown_options=True, help_option_names=['-_h', '--_help']), )
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def environment(ctx, args):
    """Info about the local environment"""

    if not args:
        args = "--help"

    data = utilities.convert_input_to_dict(ctx)
    cmd = utilities.get_commandline(SENTINEL_ENVIRONMENT, args, data)
    utilities.run_cmd(cmd)


@cli.command(context_settings=dict(ignore_unknown_options=True, help_option_names=['-_h', '--_help']), )
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def ue4(ctx, args):
    """Interact with UE4"""

    if not args:
        args = "--help"

    data = utilities.convert_input_to_dict(ctx)
    cmd = utilities.get_commandline(SENTINEL_UE4, args, data)
    utilities.run_cmd(cmd)


@cli.command(context_settings=dict(ignore_unknown_options=True, help_option_names=['-_h', '--_help']), )
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def vcs(ctx, args):
    """Interact with the Version Control System"""

    if not args:
        args = "--help"

    data = utilities.convert_input_to_dict(ctx)
    cmd = utilities.get_commandline("./sentinel_vcs/vcs_cli.py", args, data)
    utilities.run_cmd(cmd)


@cli.command(context_settings=dict(ignore_unknown_options=True, help_option_names=['-_h', '--_help']), )
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def commands(ctx, args):
    """ Utility commands"""

    if not args:
        args = "--help"

    data = utilities.convert_input_to_dict(ctx)
    cmd = utilities.get_commandline(SENTINEL_COMMANDS, args, data)
    utilities.run_cmd(cmd)


@cli.command(context_settings=dict(ignore_unknown_options=True, help_option_names=['-_h', '--_help']), )
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def database(ctx, args):

    """Interact with the Database"""

    if not args:
        args = "--help"

    data = utilities.convert_input_to_dict(ctx)

    cmd = utilities.get_commandline("./SentinelDB/SentinelDB.py", args, data)
    utilities.run_cmd(cmd)


@cli.command(context_settings=dict(ignore_unknown_options=True, help_option_names=['-_h', '--_help']), )
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def aws(ctx, args):
    """ Interact with Amazon Web Services """
    if not args:
        args = "--help"

    data = utilities.convert_input_to_dict(ctx)

    cmd = utilities.get_commandline("./SentinelAWS/SentinelAWS.py", args, data, arguments_at_end=False)
    utilities.run_cmd(cmd)


if __name__ == "__main__":
    cli()
