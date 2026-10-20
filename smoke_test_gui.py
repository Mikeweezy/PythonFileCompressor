"""
smoke_test_gui.py - Quick sanity check for the GUI.

It opens the real window, waits 3 seconds, and closes it again.
If no error appears, every widget was built successfully.

Run it with:   python smoke_test_gui.py
"""

import tkinter as tk

from gui import FileCompressorApp

root = tk.Tk()
app = FileCompressorApp(root)   # build the window
root.after(3000, root.destroy)  # auto-close after 3 seconds
root.mainloop()                 # run the window
print("GUI smoke test PASSED")