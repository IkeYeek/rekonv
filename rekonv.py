import os
import signal
from collections import deque
from io import TextIOWrapper
from types import FrameType

import click
import rich
from rich.progress import Progress
from rich.live import Live
from rich.text import Text
from rich.console import Group
import shutil
import subprocess


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


class Utils:
    INPUT_FORMATS = [
        "aiff", "aif", "au", "flac", "m4a", "mp3", "ogg", "wav", "webm", "aac",  # audio formats
        "flv", "ogv", "mov", "mp4", "m4v", "mpg", "mpeg", "mp2", "mpe", "m2v",  # video formats
    ]

    OUTPUT_FORMATS = ["aiff", "mp3", "aac", "flac"]

    CREATE_INDEX_FLUSH_BUFFER = 1000

    INDEX_PATH = os.path.abspath("./.index.rk")

    INDEX_POS_PATH = os.path.abspath("./.index-pos.rk")

    FILE_DONE = 0

    CONV_DONE = 0


IndexEntry = (str, str, bool)  # (input_path, output_path, tryConversion)
HeaderEntry = (int, int)


def get_file_name(path) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def get_file_ext(path) -> str | None:
    ext = os.path.splitext(os.path.basename(path))[1]
    return None if len(ext) < 2 else ext[1:]


def create_file_if_not_exists(path: str):
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))


def rekonv_file(target_path: str, output_path: str):
    create_file_if_not_exists(output_path)
    t = subprocess.run(["ffmpeg", "-y", "-i", target_path, output_path], capture_output=True)
    if t.returncode != 0 or not os.path.exists(output_path):
        print(t.stderr)


def escape_separators(s: str) -> str:
    return s.replace("\\", "\\\\").replace("|", "\\|")


def create_index(target: str, output_fd: str, output_format: str, skip_existing_files: bool, recursive: bool,
                 copy_all_files: bool):
    """
    creates a  index indexing all the files that will be either converted or copied during conversion stage.
    creates a  file with pickle that
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
                    if skip_existing_files and os.path.exists(output_file):  # check if file exists
                        # if skip_existing_files is set to true
                        continue
                    file = escape_separators(file)  # avoid separators in paths
                    output_file = escape_separators(output_file)
                    if file_ext in Utils.INPUT_FORMATS:
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
                    if entries_til_last_flush >= Utils.CREATE_INDEX_FLUSH_BUFFER:
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
    with open(Utils.INDEX_PATH, "w") as index_fd:
        index_fd.write(f"{num_files}, {num_to_convert}\n")

    # Step 3: Append the temporary file to the index file
    with open(temp_file_path, "r") as temp_fd, open(Utils.INDEX_PATH, "a") as index_fd:
        index_fd.write(temp_fd.read())

    # Clean up the temporary file
    os.remove(temp_file_path)


def get_index_headers(index_fd) -> (int, int):
    headers = index_fd.readline().split(",")
    return int(headers[0]), int(headers[1])


def work_from_index():
    with open(Utils.INDEX_PATH, "r") as index_fd:
        num_files, num_to_convert = get_index_headers(index_fd)
        start_files = Utils.FILE_DONE
        start_convert = Utils.CONV_DONE

        progress = Progress(auto_refresh=False)
        current_file_text = Text("Current file: ")
        render_group = Group(current_file_text, progress)

        all_files_task = progress.add_task("[yellow]All files...", total=num_files, completed=start_files)
        conversion_task = progress.add_task("[yellow]Files to convert...", total=num_to_convert,
                                            completed=start_convert)
        with Live(render_group, auto_refresh=False) as live:
            for i in range(start_files, num_files, 1):
                index_entry = index_fd.readline().split("||")
                input_file = index_entry[0].replace("\\\\", "\\").replace("\\|", "|")
                # replace separators if present in
                output_file = index_entry[1].replace("\\\\", "\\").replace("\\|", "|")
                convert = int(index_entry[2]) == 1
                render_group = Group(f"Current file: {input_file} ({i + 1}/{num_files})", progress)
                live.update(render_group)
                live.refresh()

                if convert:
                    progress.update(conversion_task, advance=1)
                    rekonv_file(input_file, output_file)
                    Utils.CONV_DONE += 1
                else:
                    create_file_if_not_exists(output_file)
                    shutil.copy(input_file, output_file)
                Utils.FILE_DONE += 1
                progress.update(all_files_task, advance=1)


def delete_index():
    if os.path.exists(Utils.INDEX_PATH):
        os.remove(Utils.INDEX_PATH)
    if os.path.exists(Utils.INDEX_POS_PATH):
        os.remove(Utils.INDEX_POS_PATH)


def check_with_index() -> None:
    if not os.path.exists(Utils.INDEX_PATH):
        raise Exception("Index file not found")
    errors = []

    with open(Utils.INDEX_PATH, "r") as ifd:
        num_files, num_to_convert = get_index_headers(ifd)
        for i in range(num_files):
            entry_raw = ifd.readline()
            if not entry_raw:
                break
            entry: IndexEntry = tuple(entry_raw.split("||"))
            if len(entry) != 3:
                raise Exception("Invalid index entry")
            if not os.path.exists(entry[1].replace("\\\\", "\\").replace("\\|", "|")):
                errors.append(entry)
    if errors:
        for error in errors:
            rich.console.Console().print(f"[red] file {error[0]} was not found at path {error[1]}")


def rekonv_batch() -> None:
    work_from_index()
    check_with_index()
    delete_index()


def rekonv(target: str, output_fd: str, output_format: str, single_file: bool, skip_existing_files: bool,
           recursive: bool, copy_all_files: bool) -> None:
    if single_file:
        rekonv_file(target, output_fd)
    else:
        create_index(target, output_fd, output_format, skip_existing_files, recursive, copy_all_files)
        rekonv_batch()
    rich.console.Console().print("[green]Done!")


def sig_handler(sig: int, _: FrameType) -> None:
    if sig == signal.SIGINT:
        while True:
            rich.console.Console().clear()
            print("Keep current position in index? [y/n]")
            keep_pos = click.prompt("", type=click.Choice(["y", "n"]))
            if keep_pos == "y":
                with open(Utils.INDEX_POS_PATH, "w") as ifd:
                    ifd.write(f"{Utils.FILE_DONE},{Utils.CONV_DONE}")
                break
            elif keep_pos == "n":
                delete_index()
                break
        raise KeyboardInterrupt


if __name__ == "__main__":
    signal.signal(signal.SIGINT, sig_handler)
    if os.path.exists(Utils.INDEX_PATH) and os.path.exists(Utils.INDEX_POS_PATH):
        with open(Utils.INDEX_POS_PATH, "r") as index_pos_file:
            file_done, conv_done = get_index_headers(index_pos_file)
            while True:
                res = click.prompt("Do you want to continue from where you left off? [y/n]",
                                   type=click.Choice(["y", "n"]))
                if res == "y":
                    Utils.FILE_DONE = int(file_done)
                    Utils.CONV_DONE = int(conv_done)
                    rekonv_batch()
                    break
                elif res == "n":
                    cli()
                else:
                    click.echo("Invalid input")

    else:
        cli()


