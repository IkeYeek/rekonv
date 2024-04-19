import os
import subprocess
from collections import deque
import click
import rich
from rich.progress import Progress
from rich.live import Live
from rich.text import Text
from rich.console import Group
import shutil
import subprocess

#


class Consts:
    INPUT_FORMATS = [
        "aiff", "aif", "au", "flac", "m4a", "mp3", "ogg", "wav", "webm", "aac",  # audio formats
        "flv", "ogv", "mov", "mp4", "m4v", "mpg", "mpeg", "mp2", "mpe", "m2v",  # video formats
    ]

    OUTPUT_FORMATS = ["aiff", "mp3", "m4a", "flac"]

    CREATE_INDEX_FLUSH_BUFFER = 1000

    INDEX_PATH = os.path.abspath("./index.rk")


IndexEntry = (str, str, bool)  # (input_path, output_path, tryConversion)
HeaderEntry = (int, int)


def get_file_name(path) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def get_file_ext(path) -> str | None:
    ext = os.path.splitext(os.path.basename(path))[1]
    return None if len(ext) < 2 else ext[1:]


@click.command()
@click.option("--target", "-t", default="./", help="target directory or file, by default \"./\"")
@click.option("--output-fd", "-o", default="./", help="output directory")
@click.option("--output-format", "-f", default="aac", type=click.Choice(["aiff", "mp3", "aac", "flac"]),
              help="output format")
@click.option("--single-file", "-sf", is_flag=True, help="convert a single file, don't forget to set a target")
@click.option("--skip-existing-files", "-skf", is_flag=True,
              help="convert a single file, don't forget to set a target")
@click.option("--recursive", "-r", is_flag=True, help="recursive")
@click.option("--copy-all-files", "-cp", is_flag=True, help="copy all files even non musics")
def cli(target: str, output_fd: str, output_format: str, single_file: bool, skip_existing_files: bool, recursive: bool,
        copy_all_files: bool):
    if single_file and target == "./":  # if for a single file, target needs to be set
        click.echo("target is mandatory for single file use")
        raise click.Abort
    if output_fd != "./":  # if output folder is not current folder, we format it properly and create it if necessary
        output_fd = os.path.abspath(output_fd)
        if not os.path.exists(output_fd):
            os.makedirs(output_fd)
    if single_file:
        # for a single file, output_fd targets the output file (and for a folder it will target the root output folder)
        output_fd = output_fd + "." + output_format
    elif single_file:
        target_path = os.path.abspath(target)  # absolute path to output target
        target_name = get_file_name(target_path)  # name of the target obtained from absolute path
        target_dir = os.path.dirname(target_path)  # directory of the target
        output_fd = os.path.join(target_dir, target_name + "." + output_format)

    rekonv(target, output_fd, output_format, single_file, skip_existing_files, recursive, copy_all_files)


def check_for_file(path: str):
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))


def rekonv_file(target_path: str, output_path: str):
    check_for_file(output_path)
    t = subprocess.run(["ffmpeg", "-y", "-i", target_path, output_path], capture_output=True)
    if t.returncode != 0 or not os.path.exists(output_path):
        print(t.stderr)


def create_index(target: str, output_fd: str, output_format: str, skip_existing_files: bool, recursive: bool,
                 copy_all_files: bool):
    """
    creates a binary index indexing all the files that will be either converted or copied during conversion stage.
    creates a binary file with pickle that
    """

    index: [IndexEntry] = []
    entries_til_last_flush = 0
    num_files = 0
    num_to_convert = 0
    output_fd = os.path.abspath(output_fd)
    target = os.path.abspath(target)
    queue = deque([(target, '')])  # Store both the directory path and its relative path from target
    temp_file_path = "temp_index_file"

    # Step 1: Create a temporary file to store the actual data
    with open(temp_file_path, "w") as temp_fd:
        while queue:
            current_dir, relative_path = queue.popleft()
            for entry in os.scandir(current_dir):
                if entry.is_file():
                    file = os.path.abspath(entry.path)
                    file_name = get_file_name(file)
                    file_ext = get_file_ext(file)
                    # Construct the output file path based on the relative path from the target
                    output_file_path = os.path.join(output_fd, relative_path, f"{file_name}.{output_format}")
                    output_file = os.path.abspath(output_file_path)
                    if skip_existing_files and os.path.exists(output_file):  # check if file exists if
                        # skip_existing_files is set to true
                        continue
                    file = file.replace("\\", "\\\\").replace("|", "\\|")  # avoid separators in titles
                    output_file = output_file.replace("\\", "\\\\").replace("|", "\\|")
                    if file_ext in Consts.INPUT_FORMATS:
                        index.append(f"{file}||{output_file}||1")
                        entries_til_last_flush += 1
                        num_files += 1
                        num_to_convert += 1
                    else:
                        if copy_all_files:
                            correct_output_name = f"{file_name}.{file_ext}" if file_ext else file_name
                            new_file_path = os.path.join(output_fd, relative_path, correct_output_name)
                            index.append(f"{file}||{new_file_path}||0")
                            entries_til_last_flush += 1
                            num_files += 1
                    if entries_til_last_flush >= Consts.CREATE_INDEX_FLUSH_BUFFER:
                        buffer = "\n".join(index)
                        temp_fd.write(buffer)
                        index.clear()
                        entries_til_last_flush = 0
                elif entry.is_dir() and recursive:
                    # Append the directory path and its relative path from target to the queue
                    queue.append((entry.path, os.path.join(relative_path, entry.name)))
        if index:  # index array is not empty
            buffer = "\n".join(index)
            temp_fd.write(buffer)

    # Step 2: Write headers to the index file
    with open(Consts.INDEX_PATH, "w") as index_fd:
        index_fd.write(f"{num_files}, {num_to_convert}\n")

    # Step 3: Append the temporary file to the index file
    with open(temp_file_path, "r") as temp_fd, open(Consts.INDEX_PATH, "a") as index_fd:
        index_fd.write(temp_fd.read())

    # Clean up the temporary file
    os.remove(temp_file_path)


def work_from_index():
    with open(Consts.INDEX_PATH, "r") as index_fd:
        headers = index_fd.readline().split(",")
        num_files = int(headers[0])
        num_to_convert = int(headers[1])

        progress = Progress(auto_refresh=False)
        current_file_text = Text("Current file: ")
        render_group = Group(current_file_text, progress)

        all_files_task = progress.add_task("[yellow]All files...", total=num_files, )
        conversion_task = progress.add_task("[yellow]Files to convert...", total=num_to_convert)
        with Live(render_group, auto_refresh=False) as live:
            for i in range(num_files):
                index_entry = index_fd.readline().split("||")
                input_file = index_entry[0].replace("\\\\", "\\").replace("\\|", "|")  # replace separators if present in
                # original titles
                output_file = index_entry[1].replace("\\\\", "\\").replace("\\|", "|")
                convert = int(index_entry[2]) == 1
                render_group = Group(f"Current file: {input_file} ({i + 1}/{num_files})", progress)
                live.update(render_group)
                live.refresh()

                if convert:
                    progress.update(conversion_task, advance=1)
                    rekonv_file(input_file, output_file)
                else:
                    check_for_file(output_file)
                    shutil.copy(input_file, output_file)
                progress.update(all_files_task, advance=1)


def rekonv(target: str, output_fd: str, output_format: str, single_file: bool, skip_existing_files: bool,
           recursive: bool, copy_all_files: bool) -> None:
    if single_file:
        rekonv_file(target, output_fd)
    else:
        create_index(target, output_fd, output_format, skip_existing_files, recursive, copy_all_files)
        work_from_index()
    rich.console.Console().print("[green]Done!")


if __name__ == "__main__":
    cli()
