import pathlib
import config_constants
import winreg
import json
import logging
import os

L = logging.getLogger()

def get_engine_path_from_windows_registry(engine_id):
    """ Read engine path from the windows registry"""

    L.info(f"Searching the registry for {engine_id}")
    reg_path = "\\".join([r"SOFTWARE\EpicGames\Unreal Engine", engine_id])

    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
    except FileNotFoundError:
        import platform

        bitness = platform.architecture()[0]
        if bitness == '32bit':
            other_view_flag = winreg.KEY_WOW64_64KEY
        elif bitness == '64bit':
            other_view_flag = winreg.KEY_WOW64_32KEY

        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path,
                                 access=winreg.KEY_READ | other_view_flag)
        except FileNotFoundError:
            '''
            We really could not find the key in both views.
            '''
            error_msg = f"unable to look up pre-installed engine version: {engine_id} from the registry"
            L.error(error_msg)
            
            print(error_msg) 
            print(f"https://docs.unrealengine.com/en-US/GettingStarted/Installation/MultipleLauncherInstalls/index.html")
            
            quit(1)

    value, regtype = winreg.QueryValueEx(key, "InstalledDirectory")
    L.info(f"Engine path found in registr{str(value)}")
    return str(value)



def add_engine_information(run_config):
    """Checks if the engine is pre-intalled and compiled or is cloned from git"""

    # TODO Change this so that it checks the the actual registry

    engine_path = run_config["environment"]["engine_root_path"]

    for each_file in os.listdir(engine_path):
        if "generateprojectfiles" in each_file.lower():

            # TODO make sure that the unreal engine structure entry actually exists before trying to add to it
            run_config["unreal_engine_structure"]["is_installed"] = False
            return run_config

    run_config["unreal_engine_structure"]["is_installed"] = True

    return run_config


def merge_dicts(original, update):
    """
    Recursively update a dict.
    Subdict's won't be overwritten but also updated.
    """

    for key, value in original.items():
        if key not in update:
            update[key] = value
        elif isinstance(value, dict):
            merge_dicts(value, update[key])
    return update


def get_engine_path_from_project_file(environment_config_data, root_dir):

    relative_path = environment_config_data["project_root_path"]
    project_root = pathlib.Path(root_dir).joinpath(relative_path).resolve()
    L.info(f"Project root: {project_root}")

    uproject_file = ""
    for each_file in project_root.glob("*.uproject"):
        uproject_file = each_file
        break

    if not uproject_file == "":

        f = open(uproject_file, "r")
        uproject_data = json.load(f)
        f.close()

        engine_association = uproject_data["EngineAssociation"]
        L.debug(f"Engine info from project file {engine_association}")
        engine = pathlib.Path(project_root).joinpath(engine_association).resolve()
        # Relative path to the engine
        
        if engine.exists():
            L.info(f"Found engine path at {engine.as_posix()}")
            return engine.as_posix()
        else:
            L.info("Searching for engine in registry")
            engine = get_engine_path_from_windows_registry(engine_association)
            return engine
    else:
        print(f"Unable to find project file in {project_root}")
        quit(1)


def _assemble_config(sentinel_environment_config):
    """Assembles all the different config files into one """

    L.debug("Loading: %s - exists: %s", sentinel_environment_config, sentinel_environment_config.exists())

    f = open(sentinel_environment_config, "r")
    environment_config_data = json.load(f)
    f.close()

    root_dir = sentinel_environment_config.parent
    L.debug("Reading environment from: %s", sentinel_environment_config)

    default_config_path = pathlib.Path(get_default_config_path())
    L.debug("Default config folder %s - Exists: %s", default_config_path, default_config_path.exists())

    default_config = _read_configs_from_directory(default_config_path)

    # Read the overwrite config
    overwrite_config_path = environment_config_data["sentinel_config_root_path"]
    overwrite_config_path = root_dir.joinpath(overwrite_config_path).resolve()
    overwrite_config = _read_configs_from_directory(overwrite_config_path)

    # Combine the run config and overwrite from the overwrite config folder
    run_config = merge_dicts(default_config, overwrite_config)

    # Add engine path

    environment_config_data = convert_environment_paths_to_abs(environment_config_data, root_dir)

    if "engine_root_path" not in environment_config_data:
        L.info("No engine Path provided in the config.  Attempting to get it from the project")
        environment_config_data["engine_root_path"] = get_engine_path_from_project_file(environment_config_data, root_dir)

    else:
        engine_config = environment_config_data["engine_root_path"]
        L.info(f"Engine path found: {engine_config}")
    
    artifacts_path = environment_config_data["sentinel_artifacts_path"]
    path = pathlib.Path(artifacts_path)

    if "gen_version_control" in run_config.keys():
        commit_id = run_config["gen_version_control"]["commit_id"]
        environment_config_data["sentinel_artifacts_path"] = path.joinpath(commit_id).as_posix()
        environment_config_data["artifact_name"] = commit_id
    elif "artifact_name" in environment_config_data:
        environment_config_data["sentinel_artifacts_path"] = path.joinpath(environment_config_data["artifact_name"]).as_posix()
    else:
        computer_name = os.getenv('COMPUTERNAME')
        environment_config_data["sentinel_artifacts_path"] = path.joinpath(computer_name).as_posix()
        environment_config_data["artifact_name"] = computer_name

    run_config[config_constants.ENVIRONMENT_CATEGORY] = environment_config_data

    # Add information about the engine
    run_config = add_engine_information(run_config)

    return run_config


def convert_environment_paths_to_abs(environment_config_data, root_dir):
    # Resolves all relative paths in the project structure to absolute paths
    for each_value in environment_config_data.keys():
        each_relative_path = environment_config_data[each_value]
        L.debug("Creating absolute paths Paths:")
        if each_relative_path.endswith("/") or each_relative_path == "":
            value = root_dir.joinpath(each_relative_path).resolve()
            L.debug(each_value + " :" + str(value) + " Exists:  " + str(value.exists()))
        else:
            value = each_relative_path

        environment_config_data[each_value] = str(value)

    return environment_config_data


def delete_all_generated_configs(default_config_path):

    root_dir = default_config_path.parent

    f = open(default_config_path, "r")
    environment_config_data = json.load(f)
    f.close()

    custom_config_root = environment_config_data["sentinel_config_root_path"]
    overwrite_config_path = root_dir.joinpath(custom_config_root).resolve()

    generated_folders = []
    for each_entry in overwrite_config_path.glob("*/"):
        if each_entry.name.startswith("gen") and each_entry.is_dir:
            generated_folders.append(each_entry)

    for each_generated_dir in generated_folders:

        # Delete the files from the directory
        for each_file in each_generated_dir.glob("*/"):
            os.remove(each_file)

        # Delete the directory
        os.rmdir(each_generated_dir)


def _read_configs_from_directory(default_config_path):
    """Creates a config file from a directory that has folders and json files"""

    run_config = {}
    temp_config_files = []
    temp_config_folders = []

    for each_entry in default_config_path.glob("*/"):
        # category
        json_data = {}
        if each_entry.is_dir():
            # Check if its a temp config folder and mark it for delete
            if each_entry.name.startswith("_"):
                temp_config_folders.append(each_entry)

            category_name = each_entry.name

            # Finding the values into the dict
            category_dict = {}

            entries = each_entry.glob("**/*.json")

            for each_sub_value in entries:

                # Reading the json file
                f = open(str(each_sub_value))
                json_data = json.load(f)
                f.close()

                # Check if its a temp config and add it to the delete list if so
                if each_sub_value.name.startswith("gen_"):
                    temp_config_files.append(each_sub_value)

                name = each_sub_value.with_suffix('').name

                category_dict[name] = json_data

            # If there was only one entry then we skip the file name and just add the category
            if len(os.listdir(each_entry)) == 1:
                run_config[category_name] = json_data
            else:
                run_config[category_name] = category_dict

    return run_config


def get_default_config_path():
    """Return the directory containing the default config folder"""
   
    # Test config file
    current_dir = pathlib.Path(pathlib.Path(__file__)).parent

    path = current_dir.joinpath("defaultConfig").resolve()
    L.debug("Default Config Path %s", current_dir)
    return path


def get_generated_config_location(environment_file):
    current_run_directory = pathlib.Path(environment_file.parent.joinpath(config_constants.GENERATED_CONFIG_FILE_NAME))

    return current_run_directory


def generate_config(environment_file):
    """Generate the assembled config based on the environment file"""
    environment_file = pathlib.Path(environment_file)

    # Assembles the config into a single file
    assembled_config_data = _assemble_config(environment_file)

    # Generate output directory
    current_run_directory = get_generated_config_location(environment_file)

    # Writing it to disk
    f = open(current_run_directory, "w")
    f.write(json.dumps(assembled_config_data, indent=4))
    f.close()

    return current_run_directory
