"""
main.py - The entry point of the PyCompressor app.

Run it with:   python main.py

It does three things:
  1. Creates the root tkinter window (the empty app "shell").
  2. Hands that window to our FileCompressorApp class from gui.py,
     which fills it with widgets and wires up all the behaviour.
  3. Starts the event loop (mainloop) - the window stays alive and
     reacts to clicks until you close it.
"""

import tkinter as tk

from gui import FileCompressorApp


def main():
    root = tk.Tk()             # 1. create the main window
    FileCompressorApp(root)    # 2. fill it with our widgets
    root.mainloop()            # 3. run until the user closes it


if __name__ == "__main__":
    main()