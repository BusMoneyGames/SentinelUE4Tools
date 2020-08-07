import json
import pathlib
import sys
import logging
import shutil
import pprint
import click

import ue4_constants
from Editor import buildcommands, commandlets, packageinspection, automationrunner
from Game import clientrunner, clientutilities

L = logging.getLogger(__name__)

def _read_config(path):
    """Reads the assembled config"""

    if path.exists():
        f = open(path, "r")
        config = json.load(f)
        f.close()

        return config
    else:
        print(f"No Config file found at: {path}")
        sys.exit(1)

def get_default_build_presets(default_run_config):
    """ Read the build presets from the config """
    return dict(default_run_config[ue4_constants.UNREAL_BUILD_SETTINGS_STRUCTURE])


def get_validate_presets(default_run_config):
    """ Read the commandlets settings from the config """
    return dict(default_run_config[ue4_constants.COMMANDLET_SETTINGS])

def is_config_valid(config):
    """Check if the config is valid"""

    env = config["environment"]

    # check if the engine root path key exists and check if the path exists on disk
    if not env["engine_root_path"]:
        print(r"Engine root key not found in config")
        print(r"This usually means that the installation of unreal was not registerd in the registry")
        print(r"It can be fixed by either Adding an entry to the  registry SOFTWARE\EpicGames\Unreal Engine or re-installing UE4")
        
        return False
    elif not pathlib.Path(env["engine_root_path"]).exists():
        print("Engine Path Not found at:" + pathlib.Path(env["engine_root_path"]).as_posix())
        return False
    else:
        return True

@click.group()
@click.option('--project_root', default="", help="Path to the config overwrite folder")
@click.option('--output', type=click.Choice(['text', 'json']), default='text', help="Output type.")
@click.option('--no_version', type=click.Choice(['true', 'false']), default='true', help="Skips output version")
@click.option('--debug', type=click.Choice(['true', 'false']), default='false',  help="Verbose logging")
@click.pass_context
def cli(ctx, project_root, debug, output,no_version):
    """Sentinel Unreal Component handles running commands interacting with unreal engine"""

    config_path = pathlib.Path(project_root).joinpath("_generated_sentinel_config.json")

    config = _read_config(config_path)
    if not is_config_valid(config):
        print("Environment config invalid... exiting")
        sys.exit(1)

    ctx.ensure_object(dict)
    ctx.obj['GENERATED_CONFIG_PATH'] = project_root
    ctx.obj['RUN_CONFIG'] = config
    ctx.obj['OUTPUT_TYPE'] = output

    # UE4 Needs to be available




@cli.group()
def build():
    """Compile and build different targets"""


@build.command()
@click.pass_context
def list_build_profiles(ctx):
    """ Lists the available build profiles"""
    run_config = ctx.obj['RUN_CONFIG']
    presets = get_default_build_presets(run_config)
    
    if ctx.obj['OUTPUT_TYPE'] == 'text':
        print("\n".join(presets.keys()))
    elif ctx.obj['OUTPUT_TYPE'] == 'json':
        print(json.dumps(presets, indent=4))


@build.command()
@click.pass_context
@click.option('-p', '--preset', default='windows_default_client', help="Build profile to run.")
@click.option('-archive', '--should_archive', type=bool, default=False, help="Should archive.")
def client(ctx, preset, should_archive):
    """ Builds client based on profile"""

    # TODO making it so that the run config is loaded in as a global argument and made available
    # to all steps

    run_config = ctx.obj['RUN_CONFIG']

    factory = buildcommands.BuilderFactory(run_config=run_config, build_config_name=preset)
    builder = factory.get_builder("Client")

    builder.pre_build_actions()
    builder.run()
    builder.post_build_actions()


@build.command()
@click.pass_context
def editor(ctx):
    """Builds editor based on profile"""
    run_config = ctx.obj['RUN_CONFIG']
    factory = buildcommands.BuilderFactory(run_config=run_config)
    builder = factory.get_builder("Editor")

    builder.pre_build_actions()
    builder.run()


@cli.group()
def project():
    """validate and extract project infrastructure information"""


@project.command()
@click.pass_context
def show_validate_profiles(ctx):
    """ output validation profiles"""
    run_config = ctx.obj['RUN_CONFIG']

    presets = get_validate_presets(run_config)

    if ctx.obj['OUTPUT_TYPE'] == 'text':
        print("\n".join(presets.keys()))
    elif ctx.obj['OUTPUT_TYPE'] == 'json':
        print(json.dumps(presets, indent=4))


@project.command()
@click.pass_context
@click.option('--task', help="Commandlet to run")
def commandlet(ctx, task):
    """ Project tasks """

    # TODO Handle the config overwrite
    run_config = ctx.obj['RUN_CONFIG']
    presets = get_validate_presets(run_config)

    if not task or task not in presets:
        print("Task: %s does not exist", task)
    else:
        commandlet = commandlets.BaseUE4Commandlet(run_config, task)
        commandlet.run()


@project.command()
@click.pass_context
def refresh_asset_info(ctx):
    """ extracts raw information about assets"""
    run_config = ctx.obj['RUN_CONFIG']

    # Runs package inspection on all the files
    inspector = packageinspection.BasePackageInspection(run_config)
    inspector.run()

    # Splits the raw inspected files into individual files
    splitter = packageinspection.RawLogSplitter(run_config, inspector.extracted_files)
    splitter.run()

    # Archive the newly created files
    packageinspection.archive_list_of_files(run_config, splitter.output_files)

    # TODO move the convert file list to the same pattern as the inspector and the splitter
    packageinspection.convert_file_list_to_json(run_config)



@cli.group()
def run():
    """Run clients"""
    pass


@run.command()
@click.pass_context
def list_test_profiles(ctx):
    """Available test profiles"""
    run_config = ctx.obj['RUN_CONFIG']
    profiles = clientutilities.get_test_profiles(run_config)

    if ctx.obj['OUTPUT_TYPE'] == 'text':
        print("\n".join(profiles.keys()))
    elif ctx.obj['OUTPUT_TYPE'] == 'json':
        print(json.dumps(profiles, indent=4))


@run.command()
@click.option('--profile', default="", help="Output type.")
@click.option('--test', default="", help="Output type.")
@click.pass_context
def run_client(ctx, profile, test):

    """Lists profiles that can be run as tests"""
    run_config = ctx.obj['RUN_CONFIG']
    available_profiles = clientutilities.get_test_profiles(run_config)

    message_output = {"Available Tests": available_profiles}
    valid_profile = False
    valid_test = False

    if not profile:
        message_output["ProfileMessage"] = "--profile argument required"
    elif profile not in available_profiles:
        message_output["ProfileMessage"] = profile + " profile was not found"
    else:
        valid_profile = True

    if not test:
        message_output["TestMessage"] = "--test argument required..."
    elif test not in available_profiles[profile]:
        message_output["TestMessage"] = test + " is not an available test"
    else:
        valid_test = True

    # If the arguments are correct
    if valid_profile and valid_test:
        message_output["Output"] = "Running build"
        runner = clientrunner.GameClientRunner(run_config, profile, test)
        if runner.does_build_exist():
            runner.run()

    else:
        # Error messages
        if ctx.obj['OUTPUT_TYPE'] == 'text':
            print("\n".join(message_output.keys()))
        elif ctx.obj['OUTPUT_TYPE'] == 'json':
            print(json.dumps(message_output, indent=4))


@run.command()
@click.pass_context
def process_client_results(ctx):

    # Find the raw test folder
    run_config = ctx.obj['RUN_CONFIG']

    print ("Not implemented")
    # ClientRunProcessor.ClientRunParser(run_config)


@cli.group()
def automation():
    """runs automation tests"""

@automation.command()
@click.pass_context
def list_automation(ctx):

    # Find the raw test folder
    run_config = ctx.obj['RUN_CONFIG']

    automationrunner.run_tests(run_config)


if __name__ == "__main__":
    cli()
