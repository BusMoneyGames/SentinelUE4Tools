import pathlib
import pprint
import json
import csv
import os 
from datetime import datetime

path = pathlib.Path(r"D:\SentinelArtifacts\GISLI-PC\Data\Packages")
out_path = pathlib.Path( r"S:\Daedalus\ProjectInfo\_data")

def get_asset_registry_headers(filter_path, asset_type=""):
    """ Return the keys based on the data that we are extracting"""
    keys = []
    number_of_files = len(list(path.glob("*.json")))

    print(asset_type)
    for i, file_path in enumerate(path.glob("*.json")):

        with open(file_path) as json_file:
            data = json.load(json_file)

            if not data["AssetType"] == asset_type:
                # Skipping types we that we don't care about
                continue


            for each_key in data["AssetRegistry"].keys():
                if each_key not in keys:
                    keys.append(each_key)

    return keys

def get_asset_types(filter_path):
    types = []
    number_of_files = len(list(path.glob("*.json")))

    for i, file_path in enumerate(path.glob("*.json")):

        with open(file_path) as json_file:
            data = json.load(json_file)

            if data["AssetType"] not in types:
                types.append(data["AssetType"])

    return types

def get_asset_registry(data):
    """ Return the asset registry if its available"""
    if "AssetRegistry" in data and "AssetImportData" in data["AssetRegistry"]:
        return data["AssetRegistry"]

def should_include(data, filter_path):
    "checks if the file is in the correct path based on the filter"
    return "AssetPath" in data and data["AssetPath"].startswith(filter_path)

def parse_asset_name(out_name, asset_type="", filter_path=""):

    file_name = asset_type + ".csv"
    out_file_path = out_path.joinpath(file_name)
    print(out_file_path)

    with open(out_file_path, 'w', newline='') as csvfile:
        header = get_asset_registry_headers(filter_path, asset_type=asset_type)
        
        header.insert(0, "AssetPath")
        header.insert(0, "RelativeFilename")
        header.insert(0, "SourceExists")
        header.insert(0, "AssetType")
        header.insert(0, "AssetName")
        header.insert(0, "Timestamp")
        writer = csv.DictWriter(csvfile, fieldnames=header)

        writer.writeheader()
        for file_path in path.glob("*.json"):
            with open(file_path) as json_file:

                data = json.load(json_file)
                if should_include(data, filter_path):
                    
                    if not data["AssetType"] == asset_type:
                        # Skipping types we that we don't care about
                        continue

                    if "AssetRegistry" in data and "AssetImportData" in data["AssetRegistry"]:
                        
                        import_data = get_asset_registry(data)
                        import_data["AssetPath"] = data["AssetPath"]
                        import_data["AssetType"] = data["AssetType"]
                        import_data["AssetName"] = data["UnrealFileName"]
                        
                        if "AssetImportData" in import_data:
                            assetImportData = import_data["AssetImportData"]

                            # TODO fix is that there is a space needed in the relative filename key
                            if "RelativeFilename " in assetImportData:
                                import_data["RelativeFilename"] = assetImportData["RelativeFilename "]
                                import_data["SourceExists"] = os.path.exists(assetImportData["RelativeFilename "])
                                if "Timestamp " in assetImportData: 
                                    ts = assetImportData["Timestamp "]
                                    if ts > 0:
                                        time_stamp = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                                        import_data["Timestamp"] = time_stamp

                            del import_data["AssetImportData"]

                        else:
                            ready_data = import_data

                        writer.writerow(import_data)

def parse_texture_data():

    for file_path in path.glob("*.json"):
        with open(file_path) as json_file:
            data = json.load(json_file)
            if "AssetType" in data and data["AssetType"] == "Texture2D":
                asset_registry = get_asset_registry(data)

                if asset_registry:
                    pprint.pprint(asset_registry)

for each_type in get_asset_types("/Content/Assets"):
    print(f"Processing {each_type}")
    parse_asset_name(path, asset_type=each_type, filter_path="/Content/Assets")
