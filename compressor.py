"""
compressor.py - The compression "engine" for the PyCompressor app.

This file contains ZERO graphical code. It only knows how to:
  1. Compress files and folders into a .zip archive
  2. Extract a .zip archive back into a folder
  3. Report progress while working (via an optional callback)

Why keep this separate from the GUI? It's a core software design idea
called "separation of concerns". Because this file knows nothing about
tkinter, you could reuse it in a command-line tool or a web app
without changing a single line.
"""

import os
import zipfile


def format_size(num_bytes):
    """Convert a byte count into a friendly string like '1.4 MB'."""
    size = float(num_bytes)
    if size < 1024:
        return f"{size:.0f} B"
    for unit in ("KB", "MB", "GB", "TB"):
        size /= 1024
        if size < 1024:
            return f"{size:.1f} {unit}"
    return f"{size:.1f} PB"


def get_total_size(paths):
    """Return the combined size (in bytes) of every file under the paths."""
    total = 0
    for path in paths:
        if os.path.isfile(path):
            total += os.path.getsize(path)
        elif os.path.isdir(path):
            # os.walk visits a folder tree: root, its subfolders, its files.
            for root, _dirs, files in os.walk(path):
                for name in files:
                    try:
                        total += os.path.getsize(os.path.join(root, name))
                    except OSError:
                        pass  # unreadable file (locked/permissions) - skip it
    return total


def compress_to_zip(paths, output_path, compression_level=6, progress_callback=None):
    """
    Compress files and/or folders into one .zip archive.

    paths             : list of file/folder paths to include
    output_path       : where to write the .zip file
    compression_level : 0 = store only (fastest), 9 = max squeeze (slowest)
    progress_callback : optional function called as cb(files_done, total_files)

    A note on the ZIP format: it stores each file separately and shrinks
    them with the DEFLATE algorithm (same family as the gzip you used in
    lesson 1). That's why .zip is universal - every OS can open it.
    """
    # Step 1: walk the given paths and collect every real file.
    files_to_add = []
    for path in paths:
        if os.path.isfile(path):
            files_to_add.append(path)
        elif os.path.isdir(path):
            for root, _dirs, files in os.walk(path):
                files_to_add.extend(os.path.join(root, name) for name in files)

    total_files = len(files_to_add)
    if total_files == 0:
        raise ValueError("Nothing to compress: no files were found.")

    # Make sure the destination folder exists (e.g. a brand-new subfolder).
    parent = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(parent, exist_ok=True)

    # Step 2: write each file into the archive, reporting progress.
    # 'with' closes the zip file automatically when we're done.
    with zipfile.ZipFile(
        output_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=compression_level,
    ) as archive:
        for files_done, file_path in enumerate(files_to_add, start=1):
            archive.write(file_path, _arcname_for(file_path, paths))
            if progress_callback is not None:
                progress_callback(files_done, total_files)

    return output_path


def _arcname_for(file_path, selected_paths):
    """
    Decide the name a file gets INSIDE the zip.

    Standalone file  -> just its filename:        "photo.jpg"
    File in a folder -> keep the folder structure: "MyFolder/docs/a.txt"

    Keeping the folder's own name means unzipping re-creates the folder
    instead of dumping loose files everywhere.
    """
    for top in selected_paths:
        if os.path.isdir(top):
            relative = os.path.relpath(file_path, top)
            if not relative.startswith(".."):  # file belongs to this folder
                return os.path.join(os.path.basename(top) or "folder", relative)
    return os.path.basename(file_path)


def extract_zip(zip_path, destination_folder, progress_callback=None):
    """
    Extract every file from a .zip archive into destination_folder.

    Returns the number of items extracted.
    """
    with zipfile.ZipFile(zip_path, "r") as archive:
        names = archive.namelist()
        for files_done, name in enumerate(names, start=1):
            archive.extract(name, destination_folder)
            if progress_callback is not None:
                progress_callback(files_done, len(names))
        return len(names)