# coding=utf-8

import pathlib
import re
import logging
L = logging.getLogger()


class PkgLogObject:

    """
    Takes in a raw pkgInfo log file and extracts relevant infomation out of it.  Saves the output file as a json file
    """

    def __init__(self, path_to_log):

        # Init the dictionary that will hold the cleaned up data
        self.log_dict = {}

        # Save the log path and read the log lines from disk
        self.log_file_path = pathlib.Path(path_to_log)

        # Saving values
        self.raw_log_lines = ""
        self.asset_name = ""
        self.absolute_package_path = ""
        self._log_chapters = []

    def _get_absolute_package_path(self):
        """
        Finds the package path from the log file from disk
        :return:
        """

        if self.absolute_package_path:
            return pathlib.Path(self.absolute_package_path)

        # Search through the file for the filename
        result = None
        for each_line in self._get_log_lines():
            result = re.search('.*?Filename: (.*).*', each_line)
            if result:
                self.absolute_package_path = result.group(1)
                break

        if not result:
            L.error("Unable to find filename in %s", self.log_file_path)

        return pathlib.Path(self.absolute_package_path)

    def get_relative_package_path(self):

        # TODO this needs to know the path to the project so that we can convert this more safely to a relative path
        part_to_split = "/Content/"
        path = self._get_absolute_package_path()
        rel_path = path.as_posix().split(part_to_split)[1]

        return part_to_split + rel_path

    def get_asset_name(self):
        """
        returns the asset name from the log file path
        :return:
        """

        package_path = self._get_absolute_package_path()

        # returns only the name of the asset as it would appear in the engine
        return package_path.stem

    def _get_log_lines(self):
        """
        Read the logs lines from disk
        :return: list of lines
        """

        if self.raw_log_lines:
            return self.raw_log_lines

        f = open(self.log_file_path, "r", encoding="utf8", errors="ignore")
        self.raw_log_lines = f.readlines()
        f.close()

        return self.raw_log_lines

    def get_data(self):

        self.log_dict["UnrealFileName"] = self.get_asset_name()
        self.log_dict["AssetPath"] = self.get_relative_package_path()
        self.log_dict["AssetType"] = self.get_asset_type()
        self.log_dict["PackageInfo"] = self.get_package_info()
        self.log_dict["PackageReferences"] = self.get_package_references()
        self.log_dict["AssetRegistry"] = self.get_asset_references()

        self.log_dict["Imports"] = []
        self.log_dict["Exports"] = []

        return self.log_dict

    def _get_chapter_from_first_line(self, first_line_string):

        package_info_chapter = []
        for each_chapter in self.get_log_chapters():
            first_line = each_chapter[0].lstrip()

            if first_line.startswith(first_line_string):
                package_info_chapter = each_chapter
                break

        return package_info_chapter

    def get_package_info(self):
        """
        Formats the package info
        :return:
        """
        package_info_chapter = self._get_chapter_from_first_line("Filename: ")

        package_info = {}
        for each_line in package_info_chapter:
            each_line = each_line.strip()

            # Skipping empty strings
            if not each_line:
                continue

            split = each_line.split(": ")
            try:
                # Adding the first and second part to the package info dict
                package_info[split[0]] = self._format_value(split[1])
            except IndexError:
                L.debug("Data parse not implemented for: %s ", each_line)

        return package_info

    def get_package_references(self):

        package_ref = {}
        package_info_chapter = self._get_chapter_from_first_line("Packages referenced by ")

        for each_line in package_info_chapter:
            each_line = each_line.lstrip().rstrip()
            line_split = each_line.split(") ")
            if line_split[0].isnumeric():
                package_ref[line_split[0]] = line_split[1]

        return package_ref

    def get_asset_type(self):
        asset_reference_chapter = self._get_chapter_from_first_line("Asset Registry Size: ")
        asset_type = ""
        for each_line in asset_reference_chapter:
            line = each_line.strip()
            # Check for the first asset reference to get the type

            asset_match_obj = re.search(r'0\) (.*?)\'', line)
            if asset_match_obj:
                asset_type = asset_match_obj.group(1)
                break

        if not asset_type:
            L.warning("Unable to determine asset type from lines: %s ", asset_reference_chapter)

        return asset_type

    def get_asset_references(self):
        asset_reference_chapter = self._get_chapter_from_first_line("Asset Registry Size: ")

        values_to_skip = ["FiBData"]

        asset_reference = {}
        for each_line in asset_reference_chapter:
            each_line = each_line.strip()

            # Skipping empty strings
            if not each_line:
                continue

            if each_line.startswith("\""):
                each_line = each_line.replace("\"", "")
                split = each_line.split(": ")

                if len(split) > 2:
                    asset_reference[split[0]] = self._split_complex_asset_data_value(each_line)
                    continue
                else:
                    try:
                        key = split[0]
                        value = split[1]

                        if key in values_to_skip:
                            continue

                        asset_reference[key] = self._format_value(value)

                    except IndexError:
                        print("Unable to parse %s ", each_line)

        return asset_reference

    def _split_complex_asset_data_value(self, line):
        """
        Deals with the case where the asset data contains multiple entries
        :param value:
        :return:
        """
        complex_data = {}
        split = line.split(": ")
        split.pop(0)
        # Joining the string and removing the first and last extra letters
        complex_value = ": ".join(split)[2:-3]

        for each_complex_pair in complex_value.split(","):
            each_complex_pair = each_complex_pair.lstrip()
            split = each_complex_pair.split(": ")
            try:
                complex_data[split[0]] = self._format_value(split[1])
            except IndexError:
                print("Unable to parse %s ", each_complex_pair)

        return complex_data

    @staticmethod
    def _format_value(value):
        try:
            value = float(value)
        except ValueError:
            # Unable to convert to float
            pass

        return value

    def get_log_chapters(self):
        """
        Split the log file into chapters
        :return:
        """

        if self._log_chapters:
            return self._log_chapters

        # Divider
        chapter_divider = "--------------------------------------------"
        lines = self._get_log_lines()
        self._log_chapters = []

        each_chapter = []
        for line_no, each_raw_line in enumerate(lines):

            if chapter_divider in each_raw_line:
                self._log_chapters.append(each_chapter)
                each_chapter = []
            else:
                each_chapter.append(each_raw_line)
            # Collecting Asset Reference

        # Adding the last one
        self._log_chapters.append(each_chapter)
        return self._log_chapters


class BaseDataParser:

    def __init__(self, lines):
        self.lines = lines
        self.data_dict = {}

    def get_dict(self):
        return self.data_dict

    @staticmethod
    def _strip_prefix_and_remove_extra_symbols(line, prefix_list):
        for prefix in prefix_list:

            line = line.replace(prefix, "").lstrip()
            line = line.replace("\n", "")

        return line

    @staticmethod
    def _get_asset_info_value(line):

        value = line.split(":")
        value.pop(0)
        value = ":".join(value)

        value = value.lstrip()

        if value.isdigit():
            value = float(value)
            return value
        else:
            return value

    @staticmethod
    def _clean_symbols_from_string(line, symbol_list):

        for each_symbol in symbol_list:
            line = line.replace(each_symbol, "")

        return line.lstrip()

    @staticmethod
    def _format_value(value_string):
        invalid_value_symbols = ["\n"]

        # Cleaning any invalid symbols
        formatted_value = BaseDataParser._clean_symbols_from_string(value_string,
                                                                    invalid_value_symbols)
        # Convert to float if value is numeric
        if value_string.isnumeric():
            formatted_value = float(value_string)
            return formatted_value

        return formatted_value


class DependencyListObject(BaseDataParser):

    def __init__(self, lines, type_of_data):

        """
        Takes in the raw line dump related to imports and exports and parses them
        :param lines: list of lines
        """

        super().__init__(lines)

        # Keeping track of which line numbers have been saved so we don't end up with
        # duplicate data
        self.processed_line_numbers = []

        self.import_prefix = "LogPackageUtilities: Display:"
        self.export_prefix = "LogPackageUtilities: Warning:"
        self.index_line_flag = type_of_data + " "
        self.all_depends_list_flag = "All Depends"
        self.depends_map_line_flag = "DependsMap"

        self.lines_to_reject_include = "LogInit: Display:"

    def get_dict(self):

        # Parsing the lines
        self.data_dict = self.parse_lines()

        return self.data_dict

    def _get_depends_infomation_from_line(self, line):

        depends_dict = {}
        split_line = line.split(" ")

        clean_index = self._clean_depends_index_(split_line[0])
        formatted_index = self._format_value(clean_index)
        depends_dict["Index"] = formatted_index

        depend_type = split_line[1]
        depends_dict["AssetType"] = self._format_value(depend_type)

        asset_full_name = split_line[2]
        depends_dict["AssetFullName"] = self._format_value(asset_full_name)

        return depends_dict

    def _is_valid_depends_line(self, line):

        split_line = line.split(" ")

        clean_index = self._clean_depends_index_(split_line[0])
        formatted_index = self._format_value(clean_index)

        # Check if the line is valid by checking the number of elements it split up into
        # and if the first index is a number

        isValid = len(split_line) >= 3 and type(formatted_index) == float

        return isValid

    def _clean_depends_index_(self, depends_index_string):

        clean_string = self._clean_symbols_from_string(depends_index_string, ["(", ")"])
        return clean_string

    def extract_depends_list(self, start_line_no):

        depends_prefixes_to_clean = ["LogPackageUtilities: Display:",
                                     "LogPackageUtilities: Warning: "]

        all_depends = []
        line_no = start_line_no
        numer_of_lines_to_check = len(self.lines)

        while line_no < numer_of_lines_to_check:
            raw_depend_line = self.lines[line_no]

            clean_depend_line = self._strip_prefix_and_remove_extra_symbols(raw_depend_line,
                                                                       depends_prefixes_to_clean)

            if self._is_valid_depends_line(clean_depend_line):
                depends_data = self._get_depends_infomation_from_line(clean_depend_line)
                all_depends.append(depends_data)
                self.processed_line_numbers.append(line_no)

                line_no = line_no + 1

            else:
                return all_depends

    def parse_lines(self):

        """
        Goes through each line of the raw input data and converts it into a dictionary

        :return: dict of data
        """

        parsed_data_dict = {}

        for line_no, each_line in enumerate(self.lines):

            if line_no in self.processed_line_numbers:
                # Skipping lines that have already been processed,  like the depends
                continue

            clean_line = self._strip_prefix_and_remove_extra_symbols(each_line,
                                                                     [self.import_prefix, self.export_prefix]
                                                                     )

            if self.index_line_flag in clean_line:

                if self.lines_to_reject_include not in clean_line:

                    name_value = self.parse_import_name(clean_line)
                    import_index_value = self.parse_import_index(clean_line)

                    # To not process this line again
                    self.processed_line_numbers.append(line_no)

                    parsed_data_dict["Name"] = self._format_value(name_value)
                    parsed_data_dict["Import Index"] = self._format_value(import_index_value)

            elif self.all_depends_list_flag in clean_line:
                all_depends = self.extract_depends_list(line_no+1)
                parsed_data_dict["AllDepends"] = all_depends

            elif self.depends_map_line_flag in clean_line:
                depends_map = self.extract_depends_list(line_no+1)
                parsed_data_dict["DependsMap"] = depends_map

            else:
                line_split = clean_line.split(" ")

                if len(line_split) > 1:
                    key = line_split[0]
                    value = line_split[1]

                    key = self._clean_symbols_from_string(key, ["'"])
                    value = self._clean_symbols_from_string(value, ["'"])

                    parsed_data_dict[key] = self._format_value(value)

        return parsed_data_dict

    def parse_import_name(self, line):
        line = line.split(":")[1]
        clean_line = self._clean_symbols_from_string(line, ["'"])

        return clean_line

    def parse_import_index(self, line):

        line = line.split(": ")[0]
        line = line.split(" ")[1]

        return line


class AssetRegistryParserObject(BaseDataParser):

    def __init__(self, lines):

        """
        Takes in the raw line dump related to asset registry imports
        """

        super().__init__(lines)
        self.prefix_to_strip = "LogPackageUtilities: Display:"

        # If the line starts with any of these symbols that its not valid
        self.invalid_line_starts = "["

    def get_dict(self):

        # Parsing the lines
        self.data_dict = self.get_asset_registry_data(self.lines)

        return self.data_dict

    def get_asset_registry_data(self, raw_registry_data_chunk):

        """
        Takes in the raw registry chunk and returns a clean dict with the data
        :return: dict
        """

        asset_registry_dict = {}

        for line_no, raw_line in enumerate(raw_registry_data_chunk):

            if self.prefix_to_strip not in raw_line:
                continue

            line = self._clean_symbols_from_string(raw_line, ["\"", self.prefix_to_strip, "\n"])
            split_line = line.split(" ")

            # Skipping lines that have an invalid line start
            if line.startswith(self.invalid_line_starts):
                continue

            # Special Case for the line that contains the name and type of the asset
            elif ")" in split_line[0]:
                # This is the name and type of the asset
                raw_asset_info_string = split_line[1].split("'")

                # Asset Name
                asset_name_key = self.validate_dict_key("AssetName")
                asset_name_value = self.validate_dic_value(raw_asset_info_string[1])

                asset_registry_dict[asset_name_key] = asset_name_value

                # Asset Type
                asset_type_key = self.validate_dict_key("AssetType")
                asset_type_value = self.validate_dic_value(raw_asset_info_string[0])

                asset_registry_dict[asset_type_key] = asset_type_value

            # Skipping FibData as it is not readable
            elif line.startswith("FiBData"):
                continue

            # Special Case for the asset import data as it contains a dictonary inside of itself
            elif line.startswith("AssetImportData"):

                asset_import_data_key = self.validate_dict_key(split_line[0])
                raw_asset_import_data = split_line
                raw_asset_import_data.pop(0)

                import_data = " ".join(raw_asset_import_data)
                import_data_dict = self.handle_asset_import_data(import_data)
                asset_registry_dict[asset_import_data_key] = import_data_dict

            else:
                # Regular key and value pair
                key = self.validate_dict_key(split_line[0])
                value = self.validate_dic_value(split_line[1])

                asset_registry_dict[key] = value

        return asset_registry_dict

    def validate_dict_key(self, input_key):
        output_key = input_key.replace(":", "").lstrip()

        return output_key

    def validate_dic_value(self, input_value):
        output_value = input_value.replace(":", "").lstrip()

        return output_value

    def handle_asset_import_data(self, data):
        data = data[3:][:-3]
        datasplit = data.split(",")

        data_dict = {}
        for each_data in datasplit:

            split_val = each_data.split(":")
            each_import_data_key = self.validate_dict_key(split_val[0].replace(" ", ""))
            split_val.pop(0)

            each_import_data_value = self.validate_dic_value(":".join(split_val))

            data_dict[each_import_data_key] = each_import_data_value

        return data_dict


class CompileBlueprints(BaseDataParser):

    def __init__(self, lines):
        super().__init__(lines)

