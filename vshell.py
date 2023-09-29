import zipfile
from argparse import ArgumentParser


def argv_parse() -> list:
    parser = ArgumentParser()
    parser.add_argument("zip", nargs=1)
    parser.add_argument("--script", nargs="?")

    argv = parser.parse_args()

    return [argv.zip, argv.script]


def catch_exception():
    a = input()
    pass


if __name__ == '__main__':
    zip_path, script_path = argv_parse()

    try:
        commands = open(script_path, "r").read().split("\n")
        print(1)
        archive = zipfile.ZipFile("/System.rar", "r")
        print(type(commands), type(archive))
    except Exception:
        catch_exception()
        exit()

    # for cmd in commands:
    argv_parse()

    a = input()
