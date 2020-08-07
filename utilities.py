import json
import os
import pathlib
import subprocess
import logging

L = logging.getLogger()

root_direction = pathlib.Path(__file__).parent

def read_config(path):
    """Reads the assembled config"""

    L.debug("Reading config from: %s - Exists: %s", path, path.exists())

    if path.exists():
        f = open(path, "r")
        config = json.load(f)
        f.close()

        return config
    else:
        L.error("Unable to find generated config at: %s ", path)
        quit(1)


def get_commandline(script_name,
                    script_commands,
                    global_arguments=None,
                    sub_command_arguments=None,
                    arguments_at_end=False):
    """
    Constructs the command line that gets passed into the different sentinel commands
    :return:
    """

    cmd = "python " + str(script_name)

    # Constructing the global arguments
    if global_arguments:
        # Creates the arguments that are passed in from the root command (sentinel.py)
        pass_through_arguments = " "
        for each_data in global_arguments.keys():
            pass_through_arguments = pass_through_arguments + each_data + "=" + global_arguments[each_data] + " "
    else:
        pass_through_arguments = ""

    # Constructing the sub command arguments
    arguments = ""
    if sub_command_arguments:
        # Creates the arguments that are local to the command in the component that is being called
        arguments = " ".join(sub_command_arguments)
    sub_command_arguments = arguments

    cmd = cmd + pass_through_arguments + " ".join(script_commands)

    # Flips the arguments to go at the end
    # TODO understand why this is needed
    if arguments_at_end:
        cmd = cmd + " " + sub_command_arguments
    else:
        cmd = cmd + " " + sub_command_arguments

    return cmd


def run_cmd(cmd, print_output=True, overwrite_exit_code=-1):
    
    return_object = ""
    if print_output:
        complete_process = subprocess.run(cmd, shell=True, cwd=root_direction)
        
        if overwrite_exit_code >= 0:
            quit(overwrite_exit_code)

        if complete_process.returncode != 0:
            quit(complete_process.returncode)

    else:
        try:
            return_object = subprocess.check_output(cmd, shell=True, text=True, cwd=root_direction)
        except subprocess.CalledProcessError as e:
            print(e)
            quit(1)

    return return_object


def convert_parameters_to_ctx(ctx, project_root, no_version, output, debug):

    if not project_root:
        run_directory = pathlib.Path(os.getcwd())
        project_root = run_directory.as_posix()

    ctx.ensure_object(dict)
    ctx.obj['PROJECT_ROOT'] = project_root
    ctx.obj['SKIP_VERSION'] = str(no_version).lower()
    ctx.obj['OUTPUT'] = str(output).lower()
    ctx.obj['DEBUG'] = str(debug).lower()

    return ctx


def convert_input_to_dict(ctx):
    data = {
        "--project_root": ctx.obj["PROJECT_ROOT"],
        "--no_version": ctx.obj['SKIP_VERSION'],
        "--output": ctx.obj['OUTPUT'],
        "--debug": ctx.obj['DEBUG']
    }
    return data


def convert_input_to_string(ctx):

    dict_input = convert_input_to_dict(ctx)
    out = ""
    for each_key in dict_input.keys():
        out = out + each_key + "=" + dict_input[each_key] + " "

    return out
