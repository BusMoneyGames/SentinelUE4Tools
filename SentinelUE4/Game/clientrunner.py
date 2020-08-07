# coding=utf-8
import pathlib
import shutil
import subprocess
import zipfile
import ue4_constants
import logging

L = logging.getLogger(__name__)


class GameClientRunner:
    """Handles running game clients"""
    def __init__(self, run_config, build_profile, test_name):
        self.test_name = test_name
        self.run_config = run_config
        self.environment_config = self.run_config[ue4_constants.ENVIRONMENT_CATEGORY]
        self.sentinel_internal_structure = self.run_config[ue4_constants.SENTINEL_PROJECT_STRUCTURE]
        self.build_profile = build_profile

        # Temp folder name:
        self.temp_folder_name = "_temp_client_run_dir"

        # TODO make this support other platforms
        self.test_suffix = ".bat"
        self.build_type_name = "WindowsNoEditor"

        self.build_zip_file_path = pathlib.Path(self.get_build_profile_path())

    def get_build_profile_path(self):
        """Finds the path the the build zip file"""
        artifacts_path = pathlib.Path(self.environment_config[ue4_constants.SENTINEL_ARTIFACTS_ROOT_PATH])

        build_folder_path = artifacts_path.joinpath(self.sentinel_internal_structure[ue4_constants.SENTINEL_BUILD_PATH])

        build_profile_path = artifacts_path.joinpath(build_folder_path, self.build_profile).with_suffix(".zip")

        L.debug("Build Profile Path: %s exists: %s", build_profile_path, build_profile_path.exists())
        return build_profile_path

    def does_build_exist(self):
        return self.build_zip_file_path.exists()

    def _extract_build_to_run_location(self, path):
        L.debug("Extracting to temporary location")

        out_path = pathlib.Path(path.parent).joinpath(self.temp_folder_name, self.build_profile, self.test_name)
        with zipfile.ZipFile(path) as zf:
            zf.extractall(out_path)

        return out_path

    def _get_client_output_target_dir(self):
        artifact_path = pathlib.Path(self.environment_config[ue4_constants.SENTINEL_ARTIFACTS_ROOT_PATH])

        client_cache_relative_path = self.sentinel_internal_structure[ue4_constants.SENTINEL_CLIENT_RUN_CACHE]

        out_path = artifact_path.joinpath(client_cache_relative_path)
        out_path = out_path.joinpath(self.build_profile, self.test_name)

        L.debug(out_path.joinpath(self.build_profile,self.test_name))

        return out_path

    def run(self):
        # Extract path to temp directory:
        build_profile_output = self._extract_build_to_run_location(self.build_zip_file_path)

        test_root = build_profile_output
        L.debug("Test Root Path: %s exists: %s", test_root, test_root.exists())

        run_cmd = test_root.joinpath(self.test_name).with_suffix(self.test_suffix)
        L.debug("run cmd path: %s exists: %s", run_cmd, run_cmd.exists())

        self._run_process(run_cmd)

        # Archive the saved folder
        # TODO figure out how to get this name somewhere else to support other platforms
        project_name = "sentinelUE4"
        saved_folder_name = "Saved"

        saved_folder = test_root.joinpath(self.build_type_name, project_name, saved_folder_name)

        target_dir = self._get_client_output_target_dir()
        # Sentinel Folder

        if target_dir.exists():
            shutil.rmtree(target_dir)

        # Archives the raw output
        shutil.copytree(saved_folder, target_dir)


        # clean the build
        # TODO Clean the whole output folder
        shutil.rmtree(build_profile_output)

    def _run_process(self, path):

        cmd = path.as_posix()
        popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        # Waiting for the process to close
        popen.wait()

        # quiting and returning with the correct return code
        if popen.returncode == 0:
            L.info("Command run successfully")
        else:
            import sys
            L.warning("Process exit with exit code: %s", popen.returncode)
            sys.exit(popen.returncode)
