import io


class CompileBlueprintParser:
    def __init__(self, log_file):

        self.log_file_path = log_file

    def get_data(self):
        split_sting = "Loading and Compiling: "
        data = {}
        capture = False

        with io.open(self.log_file_path, encoding='utf-8', errors="ignore") as infile:
            for each in infile:
                line = each

                if "===================================================================================" in each:
                    capture = False

                if split_sting in each:
                    capture = True
                    name = each.split(split_sting)[1].replace("...", "").rstrip()
                    data[name] = {"message": []}

                elif capture:
                    if "compile" and "successful" not in line.lower():
                        data[name]["message"].append(line.rstrip())

        #
        data = self.analyze_messages(data)
        return data

    def analyze_messages(self, data):
        """ Attempt to figure out what the message means """

        for each_name in data:
            message = data[each_name]["message"]

            if message:
                for each_message_line in message:
                    if "LogBlueprint: Error".lower() in each_message_line.lower():
                        data[each_name]["severity"] = "error"
                        continue

                    elif "LogBlueprint: Warning".lower() in each_message_line.lower():
                        data[each_name]["severity"] = "warning"
                        continue

                    elif "Error: [Callstack]".lower() in each_message_line.lower():
                        data[each_name]["severity"] = "critical"
                        continue
                    else:
                        data[each_name]["severity"] = "notice"


                    print(each_message_line)

        return data
