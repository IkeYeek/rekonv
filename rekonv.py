import os
import subprocess

import click
from pathlib import Path


class Consts:
    INPUT_FORMATS = [
        "aiff", "aif", "au", "flac", "m4a", "mp3", "ogg", "wav", "webm",  # audio formats
        "flv", "ogv", "mov", "mp4", "m4v", "mpg", "mpeg", "mp2", "mpe", "m2v",  # video formats
    ]
    
    OUTPUT_FORMATS = ["aiff", "mp3", "m4a", "flac"]


class BadInputFormatException(Exception):
    def __init__(self, path: str, format: str):
        super().__init__(f"Format {format} not recognized for file {path}")


def to_valid_path(path: str, iter=0) -> str:
    suffix = "" if iter == 0 else f"_{iter}"
    _, extension = os.path.splitext(path)
    basename = os.path.join(os.path.dirname(path), Path(path).stem + suffix + extension)
    if os.path.exists(basename):
        return to_valid_path(path, iter + 1)
    return basename


def konvert_file(target_path: str, output_path: str):
    _, target_extension = os.path.splitext(target_path)
    if len(target_extension) > 1 and target_extension[1:] in Consts.INPUT_FORMATS:
        valid_output_path = to_valid_path(output_path)
        valid_output_path_dir = os.path.dirname(valid_output_path)
        if not os.path.exists(valid_output_path_dir):
            os.makedirs(valid_output_path_dir)
        t = subprocess.run(["ffmpeg", "-i", target_path, valid_output_path], capture_output=True)
        if t.returncode == 0 and os.path.exists(valid_output_path):
            print(f"Converted: {target_path} -> {valid_output_path}")
        else:
            click.echo(t.stderr)
    else:
        raise BadInputFormatException(target_path, target_extension)


def konvert_batch(folder_path: str, output: str, format: str, recursive: bool):
    for (dirpath, dirnames, filenames) in os.walk(folder_path):
        if os.path.abspath(dirpath) == os.path.abspath(output):
            continue
        for filename in filenames:
            file = os.path.join(dirpath, filename)

            output_path = Path(output).joinpath(dirpath[len(folder_path)+1:], Path(file).stem + "." + format)
            try:
                konvert_file(file, output_path)
            except BadInputFormatException as e:
                click.echo(f"{e} - ignoring file")
        if not recursive:
            break


@click.command()
@click.option("--output-format", "-of",  default="aiff", type=click.Choice(["aiff", "mp3", "m4a", "flac"]), help="output format")
@click.option("--output", "-o", default="./", help="output directory")
@click.option("--single-file", "-sf",  is_flag=True, help="convert a single file, don't forget to set a target")
@click.option("--target", "-t", default="./", help="target directory or file, by default \".\"")
@click.option("--recursive", "-r", is_flag=True, help="recursive")
def rekonv(output_format, output, single_file, target, recursive):
    if single_file and target == "./":
        click.echo("target is mandatory for single file use")
        raise click.Abort
    if output != "./":
        output_fd = os.path.abspath(output)
        if single_file:
            output_fd = output_fd + "." + output_format
    elif single_file:
        target_path = os.path.abspath(target)
        target_name = Path(target_path).stem
        target_dir = os.path.dirname(target_path)
        output_fd = os.path.join(target_dir, target_name + "." + output_format)
    else:
        output_fd = "".join((os.getcwd(), "/rekonverted/"))

    target = os.path.abspath(target)

    if single_file:
        konvert_file(target, output_fd)
    else:
        konvert_batch(target, output_fd, output_format, recursive)


if __name__ == "__main__":
    rekonv()
