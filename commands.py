import click
import os
import pathlib
import utilities
import logging

L = logging.getLogger()

root_folder = pathlib.Path(__file__).parent
SENTINEL_SCRIPT_PATH = str(root_folder.joinpath("Sentinel.py"))

def refresh_config(ctx, default=False):
    data = utilities.convert_input_to_dict(ctx)

    defult_arg = str(default).lower()
    generate_config_cmd = utilities.get_commandline(SENTINEL_SCRIPT_PATH,
                                                    ["run-module",
                                                     "environment",
                                                     "generate"],
                                                    data,
                                                    sub_command_arguments=["--default="+defult_arg])

    utilities.run_cmd(generate_config_cmd)


def refresh_vcs(ctx):
    pass


@click.group()
@click.option('--project_root', default="", help="Path to the config overwrite folder")
@click.option('--output', type=click.Choice(['text', 'json']), default='text', help="Output type.")
@click.option('--no_version', type=click.Choice(['true', 'false']), default='true', help="Skips output version")
@click.option('--debug', type=click.Choice(['true', 'false']), default='false', help="Verbose logging")
@click.pass_context
def cli(ctx, project_root, output, no_version, debug):
    """Sentinel Commands"""
    if debug == 'true':
        L.setLevel(logging.DEBUG)

    ctx = utilities.convert_parameters_to_ctx(ctx,
                                              project_root=project_root,
                                              output=output,
                                              debug=debug,
                                              no_version=no_version)

    refresh_config(ctx, default=True)

    if no_version == "false":
        try:
            refresh_vcs(ctx)
        except:
            print("Unable to get version control information for run")

    refresh_config(ctx)


@cli.command()
@click.pass_context
@click.option('--preset', default="", help="Skips output version")
@click.option('--deploy_path', default="", help="If set, deploys the build to to the configured location")
@click.option('--compress', default=False, help="Compresses the artifact to a .zip file")
def build_client(ctx, preset, deploy_path, compress):
    """Builds and configures playable client"""

    global_args = utilities.convert_input_to_dict(ctx)
    cmd = utilities.get_commandline(SENTINEL_SCRIPT_PATH, ["run-module", "ue4", "build", "client"],
                                    global_arguments=global_args,
                                    sub_command_arguments=["--preset="+preset])
    utilities.run_cmd(cmd)

    if deploy_path:
        if deploy_path.lower.startswith("s3"):
            print("Dealing with s3 path")
        elif os.path.exists(deploy_path):
            print("Dealing with an os path")
        else:
            print("Unable to access access")


@cli.command()
@click.pass_context
def build_editor(ctx):
    """Builds and configures the editor"""
    data = utilities.convert_input_to_dict(ctx)
    cmd = utilities.get_commandline(SENTINEL_SCRIPT_PATH, ["run-module", "ue4", "build", "editor"], data)
    utilities.run_cmd(cmd)

@cli.command()
@click.pass_context
def build_server(ctx):
    """Builds and configures a game server"""

    print("Not implemented")


@cli.command()
@click.pass_context
def generate_lightmaps(ctx):
    """Generates lightmaps for the project"""

    data = utilities.convert_input_to_dict(ctx)

    cmd = utilities.get_commandline(SENTINEL_SCRIPT_PATH, ["run-module", "ue4", "project", "commandlet"], data, sub_command_arguments=["--task=Build-Lighting"])
    utilities.run_cmd(cmd)

@cli.command()
@click.pass_context
def generate_ddc_cache(ctx):
    """Refreshes the DDC cache for the project"""

    data = utilities.convert_input_to_dict(ctx)

    cmd = utilities.get_commandline(SENTINEL_SCRIPT_PATH, ["run-module", "ue4", "project", "commandlet"], data, sub_command_arguments=["--task=generate-ddc-cache"])
    utilities.run_cmd(cmd)

@cli.command()
@click.pass_context
def fix_up_redirectors(ctx):
    """Runs the commandlet fix up redirectors"""

    data = utilities.convert_input_to_dict(ctx)

    cmd = utilities.get_commandline(SENTINEL_SCRIPT_PATH, ["run-module", "ue4", "project", "commandlet"], data, sub_command_arguments=["--task=fixup-redirectors"])
    utilities.run_cmd(cmd)

@cli.command()
@click.pass_context
def validate_blueprints(ctx):
    """Check all blueprints in the project for errors"""

    data = utilities.convert_input_to_dict(ctx)

    cmd = utilities.get_commandline(SENTINEL_SCRIPT_PATH, ["run-module", "ue4", "project", "commandlet"], data, sub_command_arguments=["--task=Compile-Blueprints"])
    utilities.run_cmd(cmd)


@cli.command()
@click.pass_context
def validate_project(ctx):
    """Checks the dev environment for errors"""

    data = utilities.convert_input_to_dict(ctx)
    cmd = utilities.get_commandline(SENTINEL_SCRIPT_PATH, ["run-module", "ue4", "build", "editor"], data)

    # If the compile blueprints step fails then it returns an error code,  we want the step to exit succesfully
    utilities.run_cmd(cmd, overwrite_exit_code=0)


@cli.command()
@click.pass_context
def validate_packages(ctx):
    """Checks project packages for errors"""

    data = utilities.convert_input_to_dict(ctx)
    cmd = utilities.get_commandline(SENTINEL_SCRIPT_PATH, ["run-module", "ue4", "project", "refresh-asset-info"],
                                    data)
    utilities.run_cmd(cmd)


@cli.command()
@click.pass_context
def run_client_test(ctx):
    """Run automated tests for the game client"""
    pass

"""
@cli.command()
@click.option('--project_name', required=True, help="Name of the project")
@click.option('--engine_path', default="", help="Relative Path to the engine")
@click.option('--config_path', default="", help="Path to a custom config folder")
@click.option('--version_control_root', default="", help="Path to the version control root")
@click.option('--artifacts_root', default="", help="Path to the artifacts root")
@click.option('--s3_data_base_location', default="", help="path to the database location")
@click.option('--cache_path', default="", help="Path to the sentinel cache")
@click.option('--number_of_changes', default=-1, help="How far back to go")
@click.option('--prebuilt', default=False, help="Using pre built editor")
@click.pass_context
def iterate_backwards_and_execute_command(ctx,
                                          project_name,
                                          engine_path,
                                          config_path,
                                          version_control_root,
                                          s3_data_base_location,
                                          artifacts_root,
                                          cache_path,
                                          number_of_changes,
                                          prebuilt):
                                          
    """ """Goes through the history and runs validation""" """

    local_default_config_args = ["--project_name=" + project_name,
                                 "--engine_path=" + engine_path,
                                 "--config_path=" + config_path,
                                 "--version_control_root=" + version_control_root,
                                 "--s3_data_base_location=" + s3_data_base_location,
                                 "--artifacts_root=" + artifacts_root,
                                 "--cache_path=" + cache_path]

    global_args = utilities.convert_input_to_dict(ctx)

    # Command to generate the default config
    default_config_cmd = utilities.get_commandline(script_name="sentinel.py",
                                                   script_commands=["run-module", "environment",
                                                                    "make-default-config"],
                                                   global_arguments=global_args,
                                                   sub_command_arguments=local_default_config_args)

    # Command to refresh the config
    refresh_config_cmd = utilities.get_commandline(script_name="sentinel.py",
                                                   script_commands=["run-module",
                                                                    "environment",
                                                                    "generate"],
                                                   global_arguments=global_args)

    # Command refresh version control
    vcs_refresh_cmd = utilities.get_commandline(script_name="sentinel.py",
                                                script_commands=["run-module",
                                                                 "vcs",
                                                                 "refresh"],
                                                global_arguments=global_args)

    # Command to build the editor
    build_editor_cmd = utilities.get_commandline(script_name="sentinel.py",
                                                 script_commands=["run-module",
                                                                  "ue4",
                                                                  "build",
                                                                  "editor"],
                                                 global_arguments=global_args)

    # Command to refresh the asset info
    refresh_asset_info_cmd = utilities.get_commandline(script_name="sentinel.py",
                                                       script_commands=["run-module",
                                                                        "ue4",
                                                                        "project",
                                                                        "refresh-asset-info"],
                                                       global_arguments=global_args)

    utilities.run_cmd(default_config_cmd)
    utilities.run_cmd(refresh_config_cmd)
    # Reading the config to initialize the vcs walker
    config_path = pathlib.Path(ctx.obj['PROJECT_ROOT']).joinpath("_generated_sentinel_config.json")

    environment_config = utilities.read_config(config_path)
    walker = GitComponent.GitRepoWalker(environment_config)

    for i, each_commit in enumerate(walker.commits):
        walker.clean_checkout_commit(each_commit)

        utilities.run_cmd(default_config_cmd)
        # _run_component_cmd("environment make-default-config", local_default_config_args)

        utilities.run_cmd(refresh_config_cmd)
        # _run_component_cmd("environment generate")

        utilities.run_cmd(vcs_refresh_cmd)

        # _run_component_cmd("vcs refresh")
        utilities.run_cmd(refresh_config_cmd)

        # _run_component_cmd("environment generate")

        if not prebuilt:
            utilities.run_cmd(build_editor_cmd)

        utilities.run_cmd(refresh_asset_info_cmd)
        # _run_component_cmd("ue4 build editor")

        # _run_component_cmd("ue4 project refresh-asset-info")

        # Command to refresh the asset info
        write_vcs_info_cmd = utilities.get_commandline(script_name="sentinel.py",
                                                       script_commands=["run-module",
                                                                        "vcs",
                                                                        "write-history-file"],
                                                       global_arguments=global_args,
                                                       sub_command_arguments=["--commit_id=" + walker.commit_ids[i]])

        utilities.run_cmd(write_vcs_info_cmd)
        # _run_component_cmd("vcs write-history-file", "commit_id=" + walker.commit_ids[i])


        #_run_component_cmd("python aws upload-build-data")

        if i == number_of_changes:
            L.info("Maximum depth reached")
            break
"""

if __name__ == "__main__":
    cli()
