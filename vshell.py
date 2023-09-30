import re
import zipfile
from argparse import ArgumentParser
import os
import socket


def parse_argv() -> list:
    parser = ArgumentParser()
    parser.add_argument("zip", nargs=1, default=None)
    parser.add_argument("--script", nargs="?")

    argv = parser.parse_args()

    return [argv.zip[0], argv.script]


def parse_options(line):  # вычленение опций из введённой строки
    detected = re.findall(" -+\w+", line)  # опции - то, что с "-". Пример: cd -p
    all_options = list()
    for i in range(len(detected)):
        if "--" not in detected[i] and len(detected[i]) > 2:
            for j in range(2, len(detected[i])):  # короткие посимвольно сплитятся
                all_options.append("-" + detected[i][j])
    all_parameters = list(map(lambda x: x[1:].replace('"', ""),
                              re.findall('".*"| [^"^-]\S*[^"^ ]?', line)))  # параметры - это которые без "-"(путь у cd)
    return all_options, all_parameters


def is_valid_paths(zip_path, script_path) -> bool:
    if not os.path.isfile(zip_path):
        print("Invalid parameter was given: zip-file does not exist at the specified path")
        return False
    if zip_path.split(".")[-1] != "zip":
        print("Invalid parameter was given: file has to be .zip type")
        return False

    if script_path is not None:
        if not os.path.isfile(script_path):
            print("Invalid --script parameter was given: file does not exist")
            return False
        if script_path.split(".")[-1] != "txt":
            print("Invalid --script parameter was given: file has to be .txt type")
            return False

    return True


def is_valid_options(line, options, available_options):
    for token in line.split():
        if token not in options:
            break
        if token not in available_options:
            print(f"-vshell: pwd: {token}: invalid option")
            return False
    return True


class VShell:
    def __init__(self, zip_path, script_path):
        self.system = zipfile.ZipFile(zip_path, mode="r")
        self.script_path = script_path
        self.root_path = os.path.basename(zip_path).split(".")[0]
        self.local_path = os.path.basename(zip_path).split(".")[0] + "/"

    def launch_shell(self):
        if script_path:
            self.__file_input()
        else:
            self.__manual_input()

    def __manual_input(self):
        while True:
            path = self.local_path.replace(self.root_path, "~")
            print(f"root@{socket.gethostname()}:{path}#", end=" ")
            line = input()
            if line == "kill vshell":  # + os.path.basename(__file__):
                return 1

            cmd = line.split()[0]
            line = line[len(cmd):]

            self.__command_handler(cmd, line)

    def __file_input(self):
        commands = open(self.script_path, "r").read().split("\n")
        for line in commands:
            path = self.local_path.replace(self.root_path, "~")
            print(f"root@{socket.gethostname()}:{path}# {line}")

            if line == "kill vshell":
                return 1

            cmd = line.split()[0]
            line = line[len(cmd):]

            self.__command_handler(cmd, line)
        _ = input()

    def __command_handler(self, cmd, line):
        match cmd:
            case "pwd":
                options, parameters = parse_options(line)
                if is_valid_options(line, options, ["-L", "--logical", "-P", "--help"]):
                    self.pwd_execute(options)

            case "ls":
                options, parameters = parse_options(line)
                if is_valid_options(line, options, ["-Q", "-R", "-U", "-X", "-1"]):
                    self.ls_execute(options, parameters[0])

            case "cd":
                options, parameters = parse_options(line)
                if not is_valid_options(line, options, ["-L", "-P", "-e"]):
                    return

                if len(parameters) == 0:
                    print()
                    return

                if len(parameters) > 1 or line.split()[-1] in options:
                    print("vshell: cd: too many arguments")
                    return

                self.cd_execute(options, parameters[0])

            case "cat":
                options, parameters = parse_options(line)
                if not is_valid_options(line, options, ["-b", "-E", "-n", "s", "-T", "-h", "-v"]):
                    return

                if len(parameters) == 0:
                    print()
                    return

                if len(parameters) > 1 or line.split()[-1] in options:
                    print("vshell: cd: too many arguments")
                    return

                self.cat_execute(options, parameters[0])
            case _:
                print(f"{cmd}: command not found")

    def pwd_execute(self, options):
        if len(options) != 0:
            if "--help" in options:
                print("This is vshell. I'd say, vsHELL. Did you really expect any sort of help here?")
                return
            if options[0] in ["-L", "--logical"]:
                print(f"Attribute {options[0]} unavailable in this shell")

        print(self.local_path)

    def ls_execute(self, options, path):
        path = self.generate_absolute_way(path)
        sep = "  "

        responded = []

        for considered in self.system.namelist():
            if considered.startswith(path):
                if ("/" in considered[len(path):] == path and "-R" in options) or len(considered) > len(path):
                    responded.append(considered[len(path):])

        if "-Q" in options:
            for i in range(len(responded)):
                responded[i] = '"' + responded[i] + '"'

        if "-1" in options:
            sep = "\n"

        if "-X" in options:
            responded.sort()

        print(*responded, sep=sep)

    def cd_execute(self, options, path: str):
        if len(options) != 0:
            print(f"Attribute {options[-1]} unavailable in this shell")

        path = self.generate_absolute_way(path)

        if any(map(lambda x: True if x.startswith(path) and len(x) > len(path) else False, self.system.namelist())) \
                and path not in self.system.namelist():
            print(f"vshell: cd: {path}: Not a directory")
            return

        self.local_path = path

    def cat_execute(self, options, path: str):
        path = self.generate_absolute_way(path)

        if len(options) != 0:
            for option in options:
                if option in ["-s", "-h"]:
                    print(f"Attribute {option} unavailable in this shell")
                    return

        if "-v" in options:
            print("version: alpha")
            return

        if any(map(lambda x: True if x.startswith(path) and len(x) > len(path) else False, self.system.namelist())):
            print(f"vshell: cd: {path}: Not a file")
            return
        try:
            file = self.system.read(path[:-1]).decode()
        except Exception:
            file = self.system.read(path[:-1])

        file = str(file)

        if "-T" in options:
            file = file.replace("\t", "^I")

        file = re.split("\r\n|\n\r|\r|\n", file)

        if "-n" in options:
            for i in range(len(file)):
                file[i] = str(i + 1) + ": " + file[i]

        elif "-b" in options:
            for i in range(len(file)):
                if len(file[i]) > 0:
                    file[i] = str(i + 1) + ": " + file[i]

        if "-E" in options:
            for i in range(len(file)):
                file[i] = str(file[i]) + "$"

        for line in file:
            print(line)

    def generate_absolute_way(self, path: str):
        path = path.replace("\\", "/")
        if path in ["~", "/"]:
            return os.path.basename(zip_path).split(".")[0] + "/"

        path = path.split("/")

        if path[0] == self.root_path:
            return path

        absolute_way = self.local_path

        for part in path:
            if part in [".", ""]:
                continue
            if part == "..":
                if absolute_way == self.root_path:
                    continue
                absolute_way = "/".join(absolute_way.split("/")[:-2]) + "/"
            else:
                absolute_way += part + "/"
        return absolute_way


if __name__ == '__main__':
    zip_path, script_path = parse_argv()
    if not is_valid_paths(zip_path, script_path):
        exit(0)

    session = VShell(zip_path, script_path)
    print("Welcome to vshell alpha")
    session.launch_shell()
