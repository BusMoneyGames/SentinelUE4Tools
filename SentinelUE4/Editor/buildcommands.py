# coding=utf-8
import sys
import subprocess
import shutil
import os
import logging
import ue4_constants
import pathlib
from unittest.mock import MagicMock

from . import editorutilities as editorUtilities

L = logging.getLogger(__name__)


class BuilderFactory:
    def __init__(self, run_config, build_config_name=""):

        self.run_config = run_config

        # TODO deal with it if there is no build config

        if build_config_name == "":
            build_config_name = "windows_default_client"

        self.build_config_name = build_config_name
        self.should_mock = False

    def get_builder(self, builder_type):

        if builder_type == "Editor":
            builder = UnrealEditorBuilder(run_config=self.run_config)

        elif builder_type == "Client":
            # Create the builder
            builder = UnrealClientBuilder(run_config=self.run_config, build_config_name=self.build_config_name)

            if self.should_mock:
                mock_builder = MagicMock(builder)
                mock_builder.run.return_value = {"output_director": "fudge"}
                builder = mock_builder
        else:
            L.error("No builder of the type: %s", builder_type)
            builder = None
            sys.exit(4)

        return builder


class BaseUnrealBuilder:
    """
    Base class for triggering builds for an unreal engine project
    """

    def __init__(self, run_config, platform="Win64"):

        # prepare needs to be explicitly called for the build to start
        self.is_prepared = False

        self.run_config = run_config
        self.platform = platform

        self.editor_util = editorUtilities.UE4EditorUtilities(run_config, self.platform)

        self.environment_structure = self.run_config[ue4_constants.ENVIRONMENT_CATEGORY]
        self.all_build_settings = self.run_config[ue4_constants.UNREAL_BUILD_SETTINGS_STRUCTURE]

        self.project_root_path = pathlib.Path(self.environment_structure[ue4_constants.UNREAL_PROJECT_ROOT])
        self.sentinel_project_structure = self.run_config[ue4_constants.SENTINEL_PROJECT_STRUCTURE]

        sentinel_root = pathlib.Path(self.environment_structure[ue4_constants.SENTINEL_ARTIFACTS_ROOT_PATH])
        sentinel_logs_path = self.sentinel_project_structure[ue4_constants.SENTINEL_RAW_LOGS_PATH]

        self.log_output_folder = sentinel_root.joinpath(sentinel_logs_path)

        self.log_output_file_name = "Default_Log.log"

    def pre_build_actions(self):
        """
        Initializes the environment before the build starts

        :return:
        """

        # Prepare the log output file
        # Prepare the build meta data file

        self.is_prepared = True

        return {
            "Log_Location": "adfasdf",
            "Meta Data File": "123156"
        }

    def post_build_actions(self):
        pass

    @staticmethod
    def _prefix_config_with_dash(list_of_strings):

        new_list = []
        for each in list_of_strings:
            new_list.append("-"+each)

        return new_list

    def get_build_command(self):
        """
        Needs to be overwritten on child
        :return:
        """
        return ""

    def write_extra_files(self):
        pass

    def run(self):
        """
        No logic in the base class, should be overwritten on the child
        :return:
        """

        cmd = self.get_build_command()

        path = self.log_output_folder.joinpath(self.log_output_file_name)
        L.debug("output folder path: %s", path)

        if not path.parent.exists():
            os.makedirs(path.parent)

        popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        with open(path, "w", encoding='utf-8') as fp:
            for line in popen.stdout:
                line = line.decode('utf-8').rstrip()
                print(line, flush=True)
                print(line, file=fp, flush=True)

        # Waiting for the process to close
        popen.wait()

        # quiting and returning with the correct return code
        if popen.returncode == 0:
            L.info("Command run successfully")
        else:
            import sys
            L.warning("Process exit with exit code: %s", popen.returncode)
            sys.exit(popen.returncode)


class UnrealEditorBuilder(BaseUnrealBuilder):

    """
    Handle building the unreal editor binaries for the game project
    """

    def __init__(self, run_config, editor_component=""):
        """
        Uses the settings from the path object to compile the editor binaries for the project
        so that we can run a client build or commandlets
        """

        self.editor_component = editor_component

        super().__init__(run_config)
        self.editor_compile_settings = run_config[ue4_constants.UNREAL_EDITOR_COMPILE_CONFIGURATION]

        L.debug("Available editor compile targets: ")
        L.debug(", ".join(self.editor_compile_settings.keys()))

        if run_config["unreal_engine_structure"]["is_installed"]:
            compile_profile = "default_installed"
        else:
            compile_profile = "default_source"

        # TODO Support other platforms
        self.platform_compile_settings = self.editor_compile_settings[compile_profile]
        self.editor_components_to_build = self.platform_compile_settings["components"]

        self.log_output_file_name = self.sentinel_project_structure[ue4_constants.SENTINEL_DEFAULT_COMPILE_FILE_NAME]

    def get_build_command(self):
        """
        Construct the build command string
        :return: build command
        """

        if self.editor_component:
            build_target = self.editor_component
        else:
            # If no editor component is passed in we build the project
            build_target = "-project=" + "\"" + str(self.editor_util.get_project_file_path()) + "\""

        unreal_build_tool_path = str(self.editor_util.get_unreal_build_tool_path())

        cmd_list = [unreal_build_tool_path,
                    "Development",  # The editor build is always development
                    self.platform,
                    build_target,
                    ]

        # Adds teh actual editor compile flags if we are doing a full compile
        if not self.editor_component:
            compile_flags = self._prefix_config_with_dash(self.platform_compile_settings["editor_compile_flags"])
            cmd_list.extend(compile_flags)

        cmd = " ".join(cmd_list)
        L.debug("Build command: %s", cmd)

        return cmd

    def run(self):
        """
        If there are editor components ( shader compiler for example ) configured then we iterate through them first
        and build.  if there is no editor component then we build the editor directly
        :return:
        """
        if self.editor_component:
            # Only builds the component
            super(UnrealEditorBuilder, self).run()
        else:
            for i, each_component in enumerate(self.editor_components_to_build):
                L.info("%s out of %s ", str(i + 1), str(len(self.editor_components_to_build)))
                L.info("Building Editor Component: %s", each_component)
                UnrealEditorBuilder(self.run_config, editor_component=each_component).run()

            # Builds the actual editor after all the components have been built
            L.debug("Starting editor build")
            super(UnrealEditorBuilder, self).run()


class UnrealClientBuilder(BaseUnrealBuilder):
    """
    Handles making client builds of the game project that can be either archived for testing or deployed to the
    deploy location
    """

    def __init__(self, run_config, build_config_name="windows_default_client"):

        """
        Use the settings from the path object to build the client based on the settings in the settings folder
        """

        super().__init__(run_config)

        # TODO Add logic to be able to switch the build settings
        self.build_config_name = build_config_name
        self.build_settings = self.all_build_settings[self.build_config_name]

        self.platform = self.build_settings[ue4_constants.UNREAL_BUILD_PLATFORM_NAME]

        self.log_output_file_name = self.sentinel_project_structure[ue4_constants.SENTINEL_DEFAULT_COOK_FILE_NAME]

    def get_archive_directory(self):

        sentinel_output_root = self.environment_structure[ue4_constants.SENTINEL_ARTIFACTS_ROOT_PATH]
        build_folder_name = self.sentinel_project_structure[ue4_constants.SENTINEL_BUILD_PATH]
        out_dir = self.project_root_path.joinpath(sentinel_output_root, build_folder_name, self.build_config_name)

        out_dir = pathlib.Path(out_dir)
        if not out_dir.exists():
            os.makedirs(out_dir)

        return out_dir

    def post_build_actions(self):
        super().post_build_actions()

        print(self.build_settings)

        # Check if key exists and if the values are true
        if "compress" in self.build_settings and self.build_settings["compress"] is True:
            # Creates an archive
            L.debug("Starting to archive")
            build_root_directory = self.get_archive_directory()
            L.debug("Build Root: %s", build_root_directory)

             # zip_file_path =
            L.info("Starting build compression...")
            shutil.make_archive(build_root_directory, 'zip', build_root_directory)
            L.info("Build Compressed!")

            L.debug("Removing build source since we are making an archive")

            # Removing the original folder to only leave the archive
            shutil.rmtree(build_root_directory)

    def get_build_command(self):
        """
        Construct the build command string
        :return: build command
        """

        project_path = self.editor_util.get_project_file_path()

        engine_root = self.project_root_path.joinpath(self.environment_structure[ue4_constants.ENGINE_ROOT_PATH]).resolve()

        build_command_name = self.build_settings[ue4_constants.UNREAL_BUILD_COMMAND_NAME]
        build_config = self.build_settings[ue4_constants.UNREAL_BUILD_CONFIGURATION]

        # self.get_cook_list_string()

        run_uat_path = engine_root.joinpath("Engine", "Build", "BatchFiles", "RunUAT.bat")

        cmd_list = [str(run_uat_path),
                    build_command_name,
                    "-project=" + str(project_path),
                    "-clientconfig=" + build_config,
                    "-targetplatform=" + self.platform
                    ]

        config_flags = self._prefix_config_with_dash(self.build_settings[ue4_constants.UNREAL_BUILD_CONFIG_FLAGS])

        if "-archive" in config_flags:
            archive_dir_flag = "-archivedirectory=" + str(self.get_archive_directory())
            config_flags.append(archive_dir_flag)

        cmd_list.extend(config_flags)
        cmd = " ".join(cmd_list)
        L.debug(cmd)

        return cmd

    def get_cook_list_string(self):
        # all_files = self.unreal_project_info.get_all_content_files()
        all_files = []
        maps_to_package = []
        for e in all_files:

            if e.suffix == ".umap":
                lower_name = e.name.lower()
                maps_to_package.append(lower_name)
                L.debug("Adding %s to cook list", lower_name)

                # TODO Add filtering based on prefixes from the settings file

        # TODO enable the maps to package flag again
        maps_to_package_flag = "-Map=\"" + "+".join(maps_to_package) + "\""

    def run(self):
        """
        Constructs the build command and runs it
        :return: None
        """

        # TODO move the should compile flag to a constant
        if self.build_settings["should_compile"]:
            editor_builder = UnrealEditorBuilder(self.run_config)
            editor_builder.run()

        super(UnrealClientBuilder, self).run()

        self.write_run_scripts()

    def write_run_scripts(self):
        if "run_scripts" in self.build_settings:

            for each_run_script in self.build_settings["run_scripts"]:
                name = each_run_script + ".bat"
                value = self.build_settings["run_scripts"][each_run_script]

                archive_dir = self.get_archive_directory().joinpath(name)

                f = open(archive_dir, "w")
                f.write(value)
                f.close()

                L.info("Wrote run script: %s", archive_dir)
