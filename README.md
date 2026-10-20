# PyCompressor - a File Compressor with a GUI

A beginner-friendly desktop app that compresses files and folders into
`.zip` archives - and extracts them back again.

Built with **only the Python standard library**: `tkinter` for the
graphical interface and `zipfile` for the compression. Nothing to
`pip install`!

## How to run it

1. Open a terminal in this folder (`PythonFileCompressor`).
2. Run:

```text
python main.py
```

The window opens. Add files or a folder, drag the compression level
slider, press **COMPRESS!**, and pick where the `.zip` should be saved.

## Project map - what each file teaches

| File | What it is | What you learn from it |
| --- | --- | --- |
| `main.py` | Entry point: creates the window and starts the app | tkinter root window, `mainloop()` |
| `gui.py` | The whole graphical interface | widgets, layout, threads, `queue.Queue` |
| `compressor.py` | The compression engine (no GUI code) | `zipfile`, `os.walk`, callbacks |
| `lesson1_gzip_basics.py` | Your very first compression script | `gzip`, `with` blocks, reading bytes |
| `test_compressor.py` | Automated test: compress -> extract -> verify | round-trip testing, `assert` |
| `smoke_test_gui.py` | Opens the GUI for 3 seconds, then closes it | quick sanity checks |

## How it works - the big picture

```text
  You click "COMPRESS!"
          |
          v
  gui.py: start_compression()      (GUI thread - instant)
     validates input, then starts a worker
          |
          v
  _compression_worker()            (background THREAD - slow work)
     calls compressor.compress_to_zip()
     posts progress messages into a queue.Queue
          |
          v
  _poll_queue()                    (GUI thread, every 100 ms)
     reads messages -> moves progress bar -> shows results
```

This "worker thread + queue" split is why the window never freezes,
even while a big folder is being zipped.

## Key concepts to remember

1. **Separation of concerns** - `compressor.py` knows nothing about the
   GUI, so you could reuse it in a command-line tool or web app.
2. **Threads keep the GUI alive** - slow work goes in a background
   thread; the main thread keeps drawing the window.
3. **`queue.Queue` is the safe mailbox** - tkinter widgets may only be
   touched from the main thread. Workers send messages; the GUI reads them.
4. **ZIP vs GZIP** - gzip (lesson 1) shrinks ONE file's bytes. ZIP is a
   container that stores MANY files (each shrunk with DEFLATE, gzip's
   cousin) plus their names and folder structure.
5. **Compression levels 0-9** - higher = smaller file but slower.
   Text compresses great; videos/photos that are already compressed, not so much.


## Package it as an .exe (runs without installing Python!)

`make_icon.py` generates `icon.ico` using only the standard library -
open it to see exactly how the ICO/BMP binary format works. Then build:

```text
python make_icon.py
python -m PyInstaller --noconfirm --clean --onefile --windowed --name PyCompressor --icon icon.ico main.py
```

What the flags mean:

| Flag | Meaning |
| --- | --- |
| `--onefile` | pack everything into a single `.exe` |
| `--windowed` | no black console window behind the GUI |
| `--name` | the output exe name |
| `--icon` | the exe's icon file |
| `--noconfirm` | overwrite the previous build without asking |
| `--clean` | clear PyInstaller's cache for a fresh build |

Your app appears at `dist\PyCompressor.exe`. To rebuild after code
changes, rerun the command, or reuse the generated spec file:
`python -m PyInstaller PyCompressor.spec`.

Tip: `--onefile` starts a little slower (it unpacks to a temp folder on
every launch). `--onedir` starts faster but ships as a folder - try both
and see which you prefer!

## Troubleshooting

- **`ModuleNotFoundError: No module named 'compressor'`** - run
  `python main.py` from *inside* the `PythonFileCompressor` folder.
- **Window appears but nothing happens** - check the terminal for a
  traceback. Python errors always point to the file and line number.
