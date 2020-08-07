import hashlib
import io
import json
import logging
import os
import pathlib
import shutil
import subprocess

import ue4_constants
import Editor.LogProcesser.packageinfolog as PackageInfoLog
from Editor import commandlets, editorutilities


L = logging.getLogger(__name__)


class ProjectHashMap:
    """
    Takes in a list of files and generates a unique has value from them
    """

    def __init__(self, list_of_files):

        self.list_of_files = list_of_files

        self.hash_value_mapping = {}
        self.hash_values_in_project = []

        self._generate_hash_for_files()

    @staticmethod
    def _get_file_hash(file_path):
        """
        Reads a file and generates a hash value for it
        :return:
        """

        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)

        return hash_md5.hexdigest()

    def _generate_hash_for_files(self):
        """
        iterates through a list of files and generates a hash value for them
        :return:
        """

        for i, each_file in enumerate(self.list_of_files):
            file_hash_value = self._get_file_hash(each_file)

            # Making a simple list of hash values in the project
            self.hash_values_in_project.append(file_hash_value)

            # Creating a mapping with the hash value and the file path
            self.hash_value_mapping[file_hash_value] = each_file

            if i % 500 == 0:
                L.info("Generating Hash for %s out of %s", str(i), str(len(self.list_of_files)))

    def get_hash_from_filename(self, filename):

        for each_hash in self.hash_value_mapping:

            if str(self.hash_value_mapping[each_hash]) == filename:
                return each_hash

        L.warning("Unable to find hash from filename!")

        return ""

    def get_filename_from_hash(self, hash_value):

        if hash_value in self.hash_value_mapping.keys():
            return self.hash_value_mapping[hash_value]

        else:
            L.error("Unable to find file for hash: %s", hash_value)


class ExtractedDataArchive:

    """
    Handles interacting with the archive both recovering data from there as well as updating it with new data
    """

    def __init__(self, path_to_archive, file_hash_mappings):
        self.archive_folder_path = pathlib.Path(path_to_archive)
        self.project_hash_file_mappings = file_hash_mappings

        self._hash_values_in_archive = self._get_hash_values_from_archive()
        self.missing_files = []
        self.archived_files = []

    def get_missing_files(self):
        """
        """

        for each_hash in self.project_hash_file_mappings:

            if not self.is_hash_value_in_archive(each_hash):
                missing_file = self.project_hash_file_mappings[each_hash]
                self.missing_files.append(str(missing_file))

        return self.missing_files

    def get_archived_files(self):

        for each_hash in self.project_hash_file_mappings:
            if self.is_hash_value_in_archive(each_hash):
                hash_file_path = self.archive_folder_path.joinpath(each_hash + ".log")
                self.archived_files.append(hash_file_path)

        return self.archived_files

    def is_hash_value_in_archive(self, value):
        """
        Check if a hash value exists in the archive
        :param value: hash value
        :return:
        """

        if value in self._hash_values_in_archive:
            return True
        else:
            return False

    def _get_hash_values_from_archive(self):
        """
        search through the archive to look for folder names with hash values
        :return:
        """

        # TODO make it so that this can be somewhat cached but make sure that we can refresh if we know
        # That the contents of the folder has changed

        hash_values = []
        for each_file in self.archive_folder_path.glob("*"):
            each_file: pathlib.Path = each_file

            name_split = each_file.name.split(".")
            name_split.pop(-1)
            hash_value = "".join(name_split)
            hash_values.append(hash_value)

        return hash_values


class BasePackageInspection:

    def __init__(self, run_config):
        L.info("Starting Package Inspection")

        self._run_config = run_config
        self._environment_config = run_config[ue4_constants.ENVIRONMENT_CATEGORY]
        self._sentinel_structure = run_config[ue4_constants.SENTINEL_PROJECT_STRUCTURE]

        self._construct_paths()
        self._editor_util = editorutilities.UE4EditorUtilities(run_config)

        # Files that have been extracted
        self.extracted_files = []

    def _construct_paths(self):
        """Makes the paths for outputs inside of the root artifact folder"""

        self._sentinel_root = pathlib.Path(self._environment_config[ue4_constants.SENTINEL_ARTIFACTS_ROOT_PATH])
        L.debug("Sentinel Root: %s ", self._sentinel_root)

        self._archive_folder_path = pathlib.Path(self._environment_config[ue4_constants.SENTINEL_CACHE_ROOT])

        self._raw_data_dir = self._sentinel_root.joinpath(self._sentinel_structure[
                                                            ue4_constants.SENTINEL_RAW_LOGS_PATH]).resolve()

        self._processed_path = self._sentinel_root.joinpath(self._sentinel_structure[
                                                              ue4_constants.SENTINEL_PROCESSED_PATH]).resolve()

        if not self._archive_folder_path.exists():
            os.makedirs(self._archive_folder_path)
        if not self._raw_data_dir.exists():
            os.makedirs(self._raw_data_dir)
        if not self._processed_path.exists():
            os.makedirs(self._processed_path)

    def run(self):
        """
        Does a simple engine extract for asset to be able to determine asset type and other basic info
        """

        project_files = self._editor_util.get_all_content_files()
        L.info("UE project has: %s files total", len(project_files))

        # hash mapping for the files in the project
        hash_mapping = ProjectHashMap(project_files)
        L.info("Hash Mapping completed")

        # Compares the hash values with what has already been archived
        L.info("Searching archive")
        archive_object = ExtractedDataArchive(self._archive_folder_path, hash_mapping.hash_value_mapping)

        # Return a list of the missing files
        L.info("Generate missing files list")
        missing_file_list = archive_object.get_missing_files()

        L.info("Generating list of files that already exist")
        archived_files = archive_object.get_archived_files()

        L.info("Recover found files from archive")
        self._copy_archived_files_to_work_folder(archived_files)

        L.info("%s files need to be refresh", len(missing_file_list))

        chunks_of_files_to_process = split_list_into_chunks(missing_file_list, 100)

        #  This is where we go through all the to be able to get information about paths and types
        L.info("Starting file extract")
        self._extract_from_files(chunks_of_files_to_process)

    def _copy_archived_files_to_work_folder(self, archived_files):

        artifacts_path = pathlib.Path(self._run_config["environment"]["sentinel_artifacts_path"])

        for source_file in archived_files:
            source_file = pathlib.Path(source_file)
            if source_file.exists():

                target = artifacts_path.joinpath("Raw", "Packages", source_file.name)
                if not target.parent.exists():

                    os.makedirs(target.parent)
                shutil.copy(source_file, target)
            else:
                L.error("Attempting to copy a cached file that does not exist!")
                L.error("File name: %s", source_file)

    def _extract_from_files(self, chunks_of_files_to_process):

        # TODO deals the case where the user deletes files
        for i, each_chunk in enumerate(chunks_of_files_to_process):

            package_info_run_object = PackageInfoCommandlet(self._run_config, each_chunk)

            L.info("Starting chunk %s out of %s ", i + 1, str(len(chunks_of_files_to_process)))

            # Runs the extract
            package_info_run_object.run()

            # Save the file path
            self.extracted_files.append(package_info_run_object.output_file)


class PackageInfoCommandlet(commandlets.BaseUE4Commandlet):
    """ Runs the package info commandlet """
    def __init__(self, run_config, unreal_asset_file_paths):
        # Initializes the object
        super().__init__(run_config, "_PkgInfoCommandlet", files=unreal_asset_file_paths)

        self.temp_extract_dir = pathlib.Path(self.environment_config["sentinel_artifacts_path"]).joinpath("temp")
        self.output_file = ""

    def run(self):
        """
        Prepares and runs the Package info commandlet
        :return: path to the log file
        """

        commandlet_command = self.get_command()

        name = "_raw_package_info.log"
        path = pathlib.Path(self.temp_extract_dir, "0" + name)

        if not os.path.exists(self.temp_extract_dir):
            os.makedirs(self.temp_extract_dir)

        if path.exists():
            number_of_files = len(os.listdir(self.temp_extract_dir))
            path = pathlib.Path(self.temp_extract_dir, str(number_of_files) + name)

        L.info("Writing to: %s", path)

        with open(path, "w", encoding='utf-8', errors="ignore") as temp_out:
            subprocess.run(commandlet_command, stdout=temp_out, stderr=subprocess.STDOUT)

        self.output_file = path


class RawLogSplitter:
    def __init__(self, run_config, log_files):
        self._run_config = run_config
        self._log_files_list = log_files

        self._editor_util = editorutilities.UE4EditorUtilities(run_config)
        self.hash_mapping = ProjectHashMap(self._editor_util.get_all_content_files())

        self.output_files = []

    def _split_temp_log_into_raw_files(self, temp_log_path):

        """
        Split the temp file into smaller pieces in the raw folder
        :param temp_log_path:
        :return:
        """

        out_log = None

        temp_file_path = pathlib.Path(self._run_config["environment"]["sentinel_artifacts_path"]).joinpath("_temp.log")

        with io.open(temp_log_path, encoding='utf-8', errors="ignore") as infile:

            for i, line in enumerate(infile):
                if self._is_start_of_package_summary(line):

                    if not out_log:

                        # If we have never saved anything open a new file
                        out_log = io.open(temp_file_path, "w", encoding='utf-8', errors="ignore")
                        # Adding the path to the log so we can move it to the archive folder when we finish

                    else:
                        # Closing the last file that was written into
                        out_log.close()
                        # Rename the file to the guid name
                        self._move_temp_file(temp_file_path)

                        # Opening an new file with a new path
                        out_log = open(temp_file_path, "w")
                        # Adding the path to the log so we can move it to the archive folder when we finish
                if out_log:
                    # Write the data into the logs
                    try:
                        out_log.write(line + "")
                    except UnicodeEncodeError:
                        L.warning("Unable to process line" + str(i))

        # Handles the last file
        if out_log:
            out_log.close()
            self._move_temp_file(temp_file_path)

    def _move_temp_file(self, temp_file):

        # absolute path to the file
        asset_path = get_asset_path_from_log_file(temp_file)
        hash = self.hash_mapping.get_hash_from_filename(asset_path)

        artifacts_path = pathlib.Path(self._run_config["environment"]["sentinel_artifacts_path"])
        out_path = artifacts_path.joinpath("Raw", "Packages", hash + ".log")

        if not pathlib.Path(out_path.parent).exists():
            os.makedirs(out_path.parent)

        shutil.move(temp_file, out_path)
        self.output_files.append(out_path)

    def run(self):
        for each_log_file in self._log_files_list:
            self._split_temp_log_into_raw_files(each_log_file)

    @staticmethod
    def _is_start_of_package_summary(line):

        if "Package '" and "' Summary" in line:
            return True
        else:
            return False

    @staticmethod
    def _get_asset_name_from_summary_line(line):

        """
        :return: name of the asset being worked on
        """

        split = line.split(" ")
        split.pop()
        asset_path = split[len(split)-1]

        asset_path_split = asset_path.split("/")

        asset_name = asset_path_split[len(asset_path_split)-1]
        asset_name = asset_name.replace("'", "")

        return asset_name


def convert_file_list_to_json(run_config):
    """ Goes through a list of log files and converts them to json"""

    path_root = pathlib.Path(run_config["environment"]["sentinel_artifacts_path"]).joinpath("Data", "Packages")
    raw_root = pathlib.Path(run_config["environment"]["sentinel_artifacts_path"]).joinpath("Raw", "Packages")

    if not path_root.exists():
        os.makedirs(path_root)

    for each_generated_log in raw_root.glob("*/"):
        log = PackageInfoLog.PkgLogObject(each_generated_log)
        data = log.get_data()
        name = pathlib.Path(each_generated_log.with_suffix("")).name

        path = path_root.joinpath(name + ".json")

        with open(path, 'w') as outfile:
            json.dump(data, outfile, indent=4)


def split_list_into_chunks(list_to_split, max_entries_per_list):
    """
    Takes a list and splits it up into smaller lists
    """

    chunks = []
    for i in range(0, len(list_to_split), max_entries_per_list):
        chunk = list_to_split[i:i + max_entries_per_list]
        chunks.append(chunk)

    return chunks


def archive_list_of_files(run_config, list_of_files):

    cache_path = pathlib.Path(run_config["environment"]["sentinel_cache_path"])

    for source_file in list_of_files:
        source_file = pathlib.Path(source_file)
        target_file = cache_path.joinpath(source_file.name)
        shutil.copy(source_file, target_file)


# TODO move this function to the LogParser package
def get_asset_path_from_log_file(log_file_path):

    path = "Unknown"
    if not log_file_path.exists():
        L.warning("Unable to find logfile at path: %s", log_file_path)
        return path

    L.debug("Checking filename from log file: %s ", log_file_path)
    with io.open(log_file_path, encoding='utf-8', errors="ignore") as infile:

        for each in infile:
            if "Filename: " in each:
                path = each.split("Filename: ")[1].replace("\n", "")
                path = os.path.abspath(path)
                L.debug("Found filename in log file: %s", path)
                break

    if path == "Unknown":
        L.error("Unable to find path from log file path")

    return path


# TODO move this function to the LogParser package
def get_asset_type_from_log_file(log_file_path):

    log_file_path.exists()
    asset_type = "Unknown"

    if not log_file_path.exists():
        L.warning("Unable to find logfile at path: %s", log_file_path)
        return asset_type

    with io.open(log_file_path, encoding='utf-8', errors="ignore") as infile:

        for i, each in enumerate(infile):
            if "Number of assets with Asset Registry data: " in each:
                read_line = infile.readline(i + 1)
                import re
                try:
                    asset_type = re.search(r'0\) (.*?)\'', read_line).group(1)
                except AttributeError:
                    asset_type = "Unknown"
                break

    if asset_type == "Unknown":
        L.error("Unable to find type")
        print(log_file_path)

    return asset_type

