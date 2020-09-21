import logging
import pathlib
import json
import os
import logging

import click

import configelper
import config_constants

L = logging.getLogger()

def _load_environment_config(overwrite_path=""):
    """Finds the config file that contains the environment information"""
    
    # Figure out where the script is run from

    current_run_directory = pathlib.Path(os.getcwd())
    L.debug("Running from directory: %s ", current_run_directory)

    if overwrite_path:
        L.info(f"Environment path: {overwrite_path}")
    else:
        overwrite_path = ".."
        L.info("Using default path for config:  %s", overwrite_path)

    config_file_name = config_constants.CONFIG_SETTINGS_FILE_NAME
    config_file_path = current_run_directory.joinpath(overwrite_path, config_file_name).resolve()
    
    L.info(f"environment file {config_file_path} exists: {config_file_path.exists()}")

    if config_file_path.exists():
        return config_file_path
    else:
        L.error("Unable to find config environment file")
        L.error("Expected Path: %s", config_file_path)
        quit(1)

def refresh_generated_config(config_path, clean_generate=True):
    sentinel_environment_config = _load_environment_config(config_path)

    if clean_generate == "true":
        configelper.delete_all_generated_configs(sentinel_environment_config)

    configelper.generate_config(sentinel_environment_config)

@click.group()
@click.option('--project_root', default="", help="Path to the config overwrite folder")
@click.option('--output', type=click.Choice(['text', 'json']), default='text', help="Output type.")
@click.option('--no_version', type=click.Choice(['true', 'false']), default='true', help="Skips output version")
@click.option('--debug', type=click.Choice(['true', 'false']), default='false',  help="Verbose logging")
@click.pass_context
def cli(ctx, project_root, debug, output, no_version):
    """Sentinel Unreal Component handles running commands interacting with unreal engine"""

    if debug == 'true':
        L.setLevel(logging.DEBUG)

    ctx.ensure_object(dict)
    ctx.obj['CONFIG_OVERWRITE'] = project_root
    ctx.obj['SKIP_VERSION'] = no_version


@cli.command()
@click.option('-o', '--output', type=click.Choice(['text', 'json']), default='text', help="Output type.")
@click.option('--default', type=click.Choice(['true', 'false']), default='false', help="generates the default config")
@click.pass_context
def generate(ctx, output, default):
    """Generates a config file """

    config_path = ctx.obj['CONFIG_OVERWRITE']
    refresh_generated_config(config_path, default)


@cli.command()
@click.argument('values', nargs=-1)
@click.pass_context
def get_config_environment_value(ctx, values):
    config_path = ctx.obj['CONFIG_OVERWRITE']
    environment_config = _load_environment_config(config_path)
    generated_config = configelper.get_generated_config_location(environment_config)

    out = []
    with open(generated_config) as json_file:
        data = json.load(json_file)["environment"]
        for val in values:
            if val in data:
                out.append(data[val])
            else:
                print("Unable to find : %s in environment config", val)

    print(" ".join(out))

@cli.command()
@click.option('--project_name', default="", help="Name of the project")
@click.option('--engine_path', default="", help="Relative Path to the engine")
@click.option('--config_path', default="", help="Path to a custom config folder")
@click.option('--artifact_name', default="", help="Artifact Name")
@click.option('--version_control_root', default="", help="Path to the version control root")
@click.option('--artifacts_root', default="", help="Path to the artifacts root")
@click.option('--s3_data_base_location', default="", help="Path to the database")
@click.option('--sentinel_database', default="", help="Path to the sentinel database")
@click.option('--cache_path', default="", help="Path to the sentinel cache")
@click.pass_context
def make_default_config(ctx, project_name,
                        engine_path,
                        artifact_name,
                        config_path,
                        version_control_root,
                        artifacts_root,
                        sentinel_database,
                        s3_data_base_location,
                        cache_path):

    """Generate the default config for an unreal project"""

    L.info("Generating default config")

    default_config_path = pathlib.Path(ctx.obj['CONFIG_OVERWRITE']).joinpath("_sentinel_root.json")

    if not project_name:
        project_name = ""
    if not config_path:
        config_path = "SentinelConfig/"
    if not version_control_root:
        version_control_root = ""
    if not artifacts_root:
        artifacts_root = "SentinelArtifacts/"
    if not sentinel_database:
        sentinel_database = "SentinelDB/"
    if not cache_path:
        cache_path = "SentinelCache/"
    if not s3_data_base_location:
        s3_data_base_location = "Not Set"

    config = {"project_root_path": project_name,
              "sentinel_config_root_path": config_path,
              "version_control_root": version_control_root,
              "sentinel_artifacts_path": artifacts_root,
              "sentinel_database": sentinel_database,
              "sentinel_cache_path": cache_path,
              "s3_data_base_location": s3_data_base_location}

    
    if engine_path:
        config["engine_root_path"] =  engine_path

    if artifact_name:
        config["artifact_name"] =  artifact_name

    f = open(default_config_path, "w")
    f.write(json.dumps(config, indent=4))
    f.close()

if __name__ == "__main__":
    cli()
