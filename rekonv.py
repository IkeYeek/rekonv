import concurrent.futures
import os
from collections import deque

import click
import rich
from rich.progress import Progress
from rich.live import Live
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
    """
    A command-line interface function that converts audio files to a specified output format.

    Parameters:
        target (str): The target directory or file to convert. Default is "./".
        output_fd (str): The output directory. Default is "./".
        output_format (str): The output format. Default is "aac".
        single_file (bool): Flag indicating whether to convert a single file. Default is False.
        skip_existing_files (bool): Flag indicating whether to skip existing files. Default is False.
        recursive (bool): Flag indicating whether to convert files recursively. Default is False.
        copy_all_files (bool): Flag indicating whether to copy all files, even non-music files. Default is False.

    Raises:
        click.Abort: If the target is not set for single file conversion.

    Returns:
        None
    """
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
    MAX_CONCURRENT_CONVERSIONS = 16
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

    STOP_PROGRAM = False


IndexEntry = (str, str, bool)  # (input_path, output_path, tryConversion)
HeaderEntry = (int, int)


def get_file_name(path) -> str:
    """
    Returns the file name without the extension from the given path.

    Parameters:
        path (str): The path of the file.

    Returns:
        str: The file name without the extension.
    """
    return os.path.splitext(os.path.basename(path))[0]


def get_file_ext(path) -> str | None:
    """
    Returns the file extension from the given path.

    Parameters:
        path (str): The path of the file.

    Returns:
        str | None: The file extension or None if the extension is empty or has less than 2 characters.
    """
    ext = os.path.splitext(os.path.basename(path))[1]
    return None if len(ext) < 2 else ext[1:]


def create_file_if_not_exists(path: str):
    """
    Create a file if it does not already exist.

    Parameters:
        path (str): The path of the file to create.

    Returns:
        None
    """
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))


def rekonv_file(target_path: str, output_path: str):
    """
    Convert a single audio file from the given target path to the specified output path using ffmpeg.

    Parameters:
        target_path (str): The path of the input audio file.
        output_path (str): The path of the output audio file.

    Returns:
        None
    """
    print(output_path)
    create_file_if_not_exists(output_path)
    t = subprocess.run(["ffmpeg", "-y", "-i", target_path, output_path], capture_output=True)
    if t.returncode != 0 or not os.path.exists(output_path):
        print(t.stderr)


def escape_separators(s: str) -> str:
    """
    A function that escapes '\' and '|' in the input string.

    Parameters:
        s (str): The input string to escape separators from.

    Returns:
        str: The input string with '\\' and '|' escaped.
    """
    return s.replace("\\", "\\\\").replace("|", "\\|")


def unescape_separators(s: str) -> str:
    """
    A function that unescapes '\' and '|' in the input string.

    Parameters:
        s (str): The input string to unescape separators from.

    Returns:
        str: The input string with '\\' and '|' unescaped.
    """
    return s.replace("\\\\", "\\").replace("\\|", "|")


def create_index(target: str, output_fd: str, output_format: str, skip_existing_files: bool, recursive: bool,
                 copy_all_files: bool):
    """
    Create an index of files to be converted from the given target directory. The index is stored in a temporary file
    and then appended to the main index file. The main index file contains the number of files and the number of files
    to be converted.

    Parameters:
        target (str): The target directory to create the index from.
        output_fd (str): The output directory where the converted files will be stored.
        output_format (str): The output format of the converted files.
        skip_existing_files (bool): Flag indicating whether to skip existing files in the output directory.
        recursive (bool): Flag indicating whether to recursively create the index from subdirectories.
        copy_all_files (bool): Flag indicating whether to copy all files, including non-music files, to the output directory.

    Returns:
        None
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
    """
    Reads the first line of the given file object `index_fd` and splits it by comma.
    Parses the resulting list into two integers representing the headers of the index.

    :param index_fd: A file object to read the first line from.
    :type index_fd: file object

    :return: A tuple of two integers representing the headers of the index.
    :rtype: tuple(int, int)
    """
    headers = index_fd.readline().split(",")
    return int(headers[0]), int(headers[1])


def work_from_index():
    """
    A function that processes the index file, handles file conversions, and updates progress.
    Can start from Utls.FILE_DONE/Utils.CONV_DONE.
    """
    try:
        with open(Utils.INDEX_PATH, "r") as index_fd:
            num_files, num_to_convert = get_index_headers(index_fd)
            start_files = Utils.FILE_DONE
            start_convert = Utils.CONV_DONE

            progress = Progress(auto_refresh=False)

            all_files_task = progress.add_task("[yellow]All files...", total=num_files, completed=start_files)
            conversion_task = progress.add_task("[yellow]Files to convert...", total=num_to_convert,
                                                completed=start_convert)
            with Live(progress, auto_refresh=False) as live, concurrent.futures.ProcessPoolExecutor() as executor:
                futures = []
                for i in range(0, start_files, 1):
                    index_entry = index_fd.readline().split("||")
                    output_file = unescape_separators(index_entry[1])
                    print(f"skipping file {output_file}")
                for i in range(start_files, num_files, 1):
                    index_entry = index_fd.readline().split("||")
                    input_file = unescape_separators(index_entry[0])
                    # replace separators if present in
                    output_file = unescape_separators(index_entry[1])
                    convert = int(index_entry[2]) == 1

                    if convert:
                        #rekonv_file(input_file, output_file)
                        futures.append(executor.submit(rekonv_file, input_file, output_file))

                    else:
                        create_file_if_not_exists(output_file)
                        progress.update(all_files_task, advance=1)
                        shutil.copy(input_file, output_file)
                        Utils.FILE_DONE += 1
                    while len(futures) > Utils.MAX_CONCURRENT_CONVERSIONS:
                        handle_future_termination(all_files_task, conversion_task, futures, progress)
                        live.refresh()
                while len(futures) > 0:
                    handle_future_termination(all_files_task, conversion_task, futures, progress)
                    live.refresh()
    finally:
        index_fd.close()
        with open(Utils.INDEX_POS_PATH, "w") as ifd:
            ifd.write(f"{Utils.FILE_DONE},{Utils.CONV_DONE}")


def handle_future_termination(all_files_task, conversion_task, futures, progress):
    """
    Updates the progress bar and removes completed tasks from the list of futures.

    Parameters:
        all_files_task (int): The task ID for the "All files" progress bar.
        conversion_task (int): The task ID for the "Files to convert" progress bar.
        futures (list): A list of concurrent.futures.Future objects representing the tasks.
        progress (rich.progress.Progress): The progress bar object.

    Returns:
        None
    """
    tasks_done = filter(lambda x: x.done(), futures)
    for task in tasks_done:
        Utils.FILE_DONE += 1
        Utils.CONV_DONE += 1
        progress.update(all_files_task, advance=1)
        progress.update(conversion_task, advance=1)
        futures.remove(task)


def delete_index():
    """
    Deletes the index file and index position file if they exist.

    This function checks if the index file and index position file exist using the `os.path.exists()` function. If the index file exists, it is deleted using the `os.remove()` function. Similarly, if the index position file exists, it is deleted.

    Parameters:
        None

    Returns:
        None
    """
    if os.path.exists(Utils.INDEX_PATH):
        os.remove(Utils.INDEX_PATH)
    if os.path.exists(Utils.INDEX_POS_PATH):
        os.remove(Utils.INDEX_POS_PATH)


def check_with_index() -> None:
    """
    Check the index file for errors and report any missing files.

    This function checks if the index file exists and raises an exception if it does not.
    It then reads the index file line by line and checks if each entry is valid.
    Finally, if there are any errors, they are reported to the console.

    Parameters:
        None

    Returns:
        None
    """
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
            if not os.path.exists(unescape_separators(entry[1])):
                errors.append(entry)
    if errors:
        for error in errors:
            rich.console.Console().print(f"[red] file {error[0]} was not found at path {error[1]}")


def rekonv_batch() -> None:
    """
    Executes a batch conversion of files by calling the `work_from_index` function,
    `check_with_index` function, and `delete_index` function in sequence.

    Parameters:
        None

    Returns:
        None
    """
    work_from_index()
    check_with_index()
    delete_index()


def rekonv(target: str, output_fd: str, output_format: str, single_file: bool, skip_existing_files: bool,
           recursive: bool, copy_all_files: bool) -> None:
    """
    Converts audio files to a specified output format.

    Args:
        target (str): The target directory or file to convert. Default is "./".
        output_fd (str): The output directory. Default is "./".
        output_format (str): The output format. Default is "aac".
        single_file (bool): Flag indicating whether to convert a single file. Default is False.
        skip_existing_files (bool): Flag indicating whether to skip existing files. Default is False.
        recursive (bool): Flag indicating whether to convert files recursively. Default is False.
        copy_all_files (bool): Flag indicating whether to copy all files, even non-music files. Default is False.

    Returns:
        None

    This function converts audio files to a specified output format. If `single_file` is True, it converts a single file
    specified by `target` to the output format specified by `output_format`. If `single_file` is False, it creates an
    index of files to be converted from the given target directory and then executes a batch conversion of files. The
    converted files are stored in the output directory specified by `output_fd`. If `skip_existing_files` is True, it
    skips existing files in the output directory. If `recursive` is True, it recursively creates the index from subdirectories.
    If `copy_all_files` is True, it copies all files, including non-music files, to the output directory. After the conversion
    is done, it prints "Done!" to the console using the rich library.
    """
    if single_file:
        rekonv_file(target, output_fd)
    else:
        create_index(target, output_fd, output_format, skip_existing_files, recursive, copy_all_files)
        rekonv_batch()
    rich.console.Console().print("[green]Done!")


if __name__ == "__main__":
    index_path_exists = os.path.exists(Utils.INDEX_PATH)
    index_pos_path_exists = os.path.exists(Utils.INDEX_POS_PATH)

    if index_path_exists and index_pos_path_exists:
        with open(Utils.INDEX_POS_PATH, "r") as index_pos_file:
            file_done, conv_done = get_index_headers(index_pos_file)
            continue_prompt = True

            while continue_prompt:
                response = click.prompt("Do you want to continue from where you left off? [y/n]",
                                        type=click.Choice(["y", "n"]))
                if response == "y":
                    Utils.FILE_DONE = int(file_done)
                    Utils.CONV_DONE = int(conv_done)
                    rekonv_batch()
                    continue_prompt = False
                elif response == "n":
                    cli()
                    continue_prompt = False
                else:
                    click.echo("Invalid input")
    else:
        cli()



