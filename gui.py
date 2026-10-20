"""
gui.py - Builds the graphical window for the PyCompressor app.

Big ideas you can learn from this file:

1. WIDGETS - tkinter gives us ready-made building blocks: Label,
   Button, Listbox, Entry, Scale, Text, Progressbar. We arrange them
   with .pack() (top to bottom) and helper Frames.

2. DON'T BLOCK THE GUI - compressing can take many seconds. If we did
   that work inside a button handler, the whole window would freeze.
   So the heavy lifting runs in a separate *thread* (see PART 4).

3. THREAD SAFETY - tkinter is NOT thread-safe: a background thread
   must never touch widgets. Instead, the worker drops messages into
   a queue.Queue "mailbox", and the main thread checks that mailbox
   10 times per second with root.after() (see PART 5). This is the
   standard, safe pattern for tkinter apps.
"""

import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from compressor import (
    compress_to_zip,
    extract_zip,
    format_size,
    get_total_size,
)


class FileCompressorApp:
    """Owns the whole window and everything that happens inside it."""

    def __init__(self, root):
        self.root = root
        root.title("PyCompressor - File Compressor")
        root.geometry("700x620")
        root.minsize(620, 540)

        self.selected_paths = []            # what the user wants to compress
        self.message_queue = queue.Queue()  # mailbox: worker thread -> GUI

        self._build_widgets()
        root.after(100, self._poll_queue)   # start checking the mailbox

    # ==================================================================
    # PART 1: BUILD THE WINDOW LAYOUT (runs once at startup)
    # ==================================================================
    def _build_widgets(self):
        # ---- Title ----
        ttk.Label(
            self.root, text="PyCompressor", font=("Segoe UI", 18, "bold"),
        ).pack(pady=(14, 0))
        ttk.Label(
            self.root, text="Squash files and folders into a .zip archive",
        ).pack()

        # ---- Step 1: the list of chosen files/folders ----
        list_frame = ttk.LabelFrame(self.root, text=" 1. Choose what to compress ")
        list_frame.pack(fill="x", padx=14, pady=8)

        list_row = ttk.Frame(list_frame)
        list_row.pack(fill="both", expand=True, padx=10, pady=10)

        # Listbox + scrollbar: each needs to know about the other,
        # which is why we call .config() after creating both.
        self.file_listbox = tk.Listbox(list_row, height=7, selectmode=tk.EXTENDED)
        self.file_listbox.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_row, command=self.file_listbox.yview)
        scrollbar.pack(side="left", fill="y")
        self.file_listbox.config(yscrollcommand=scrollbar.set)

        button_row = ttk.Frame(list_frame)
        button_row.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(button_row, text="Add Files...", command=self.add_files).pack(side="left")
        ttk.Button(button_row, text="Add Folder...", command=self.add_folder).pack(side="left", padx=6)
        ttk.Button(button_row, text="Remove Selected", command=self.remove_selected).pack(side="left")
        ttk.Button(button_row, text="Clear All", command=self.clear_all).pack(side="right")

        # ---- Step 2: settings ----
        settings_frame = ttk.LabelFrame(self.root, text=" 2. Settings ")
        settings_frame.pack(fill="x", padx=14, pady=8)

        level_row = ttk.Frame(settings_frame)
        level_row.pack(fill="x", padx=10, pady=(10, 0))
        ttk.Label(level_row, text="Compression level:").pack(side="left")
        # 0 = no shrinking (fastest), 9 = maximum squeeze (slowest).
        self.level_var = tk.DoubleVar(value=6.0)
        ttk.Scale(
            level_row, from_=0, to=9, orient="horizontal",
            variable=self.level_var, command=self._update_level_label,
        ).pack(side="left", fill="x", expand=True, padx=10)
        self.level_label = ttk.Label(level_row, text="6", width=22)
        self.level_label.pack(side="left")

        output_row = ttk.Frame(settings_frame)
        output_row.pack(fill="x", padx=10, pady=(8, 10))
        ttk.Label(output_row, text="Save zip to:").pack(side="left")
        self.output_var = tk.StringVar()  # the Entry displays this text
        ttk.Entry(output_row, textvariable=self.output_var).pack(
            side="left", fill="x", expand=True, padx=8)
        ttk.Button(output_row, text="Browse...", command=self.choose_output).pack(side="left")

        # ---- Step 3: the action buttons ----
        actions_frame = ttk.Frame(self.root)
        actions_frame.pack(pady=6)
        self.compress_button = ttk.Button(
            actions_frame, text="COMPRESS!", command=self.start_compression, width=16)
        self.compress_button.pack(side="left", padx=6)
        self.extract_button = ttk.Button(
            actions_frame, text="Extract a .zip", command=self.start_extraction, width=16)
        self.extract_button.pack(side="left", padx=6)

        # ---- Progress bar + status message ----
        progress_frame = ttk.LabelFrame(self.root, text=" Progress ")
        progress_frame.pack(fill="x", padx=14, pady=8)
        self.progress = ttk.Progressbar(progress_frame, maximum=100)
        self.progress.pack(fill="x", padx=10, pady=(10, 4))
        self.status_label = ttk.Label(
            progress_frame, text="Ready. Add some files to get started!")
        self.status_label.pack(anchor="w", padx=10, pady=(0, 10))

        # ---- Results log (a read-only Text widget) ----
        results_frame = ttk.LabelFrame(self.root, text=" Results ")
        results_frame.pack(fill="both", expand=True, padx=14, pady=(8, 14))
        self.results_text = tk.Text(results_frame, height=8, state="disabled", wrap="word")
        self.results_text.pack(fill="both", expand=True, padx=6, pady=6)

    # ==================================================================
    # PART 2: SMALL HELPERS (list box, file pickers, logging)
    # ==================================================================
    def _update_level_label(self, _value=None):
        level = int(round(self.level_var.get()))
        hints = {0: "stored only", 1: "fastest", 9: "smallest"}
        hint = hints.get(level, "strong" if level >= 7 else "balanced")
        self.level_label.config(text=f"{level}  ({hint})")

    def add_files(self):
        paths = filedialog.askopenfilenames(title="Choose files to compress")
        self._add_paths(paths)

    def add_folder(self):
        path = filedialog.askdirectory(title="Choose a folder to compress")
        if path:
            self._add_paths([path])

    def _add_paths(self, paths):
        for path in paths:
            if path not in self.selected_paths:  # avoid duplicates
                self.selected_paths.append(path)
        self._refresh_listbox()

    def remove_selected(self):
        # reversed() so deleting from the back doesn't shift the
        # indices of the items we haven't deleted yet.
        for index in reversed(self.file_listbox.curselection()):
            del self.selected_paths[index]
        self._refresh_listbox()

    def clear_all(self):
        self.selected_paths.clear()
        self._refresh_listbox()

    def _refresh_listbox(self):
        self.file_listbox.delete(0, "end")
        for path in self.selected_paths:
            self.file_listbox.insert("end", path)
        self.status_label.config(text=f"{len(self.selected_paths)} item(s) selected.")

    def choose_output(self):
        path = filedialog.asksaveasfilename(
            title="Choose where to save the zip",
            defaultextension=".zip",
            filetypes=[("Zip archive", "*.zip")],
        )
        if path:
            self.output_var.set(path)

    def _log(self, text):
        """Append text to the Results box. The Text widget is normally
        read-only, so we briefly flip its state to 'normal' to write."""
        self.results_text.config(state="normal")
        self.results_text.insert("end", text + "\n")
        self.results_text.see("end")  # auto-scroll to the newest line
        self.results_text.config(state="disabled")

    def _set_busy(self, busy, status_text=None):
        """Disable buttons while a job runs (so the user can't start two
        jobs at once) and reset the progress bar to zero."""
        state = "disabled" if busy else "normal"
        self.compress_button.config(state=state)
        self.extract_button.config(state=state)
        if status_text is not None:
            self.status_label.config(text=status_text)
        if busy:
            self.progress["value"] = 0

    # ==================================================================
    # PART 3: START JOBS (GUI thread - quick, no heavy work here)
    # ==================================================================
    def start_compression(self):
        if not self.selected_paths:
            messagebox.showwarning(
                "Nothing selected", "Add at least one file or folder first.")
            return

        output_path = self.output_var.get().strip()
        if not output_path:
            # Friendly default: save to the Desktop.
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            output_path = os.path.join(desktop, "compressed_files.zip")
        if not output_path.lower().endswith(".zip"):
            output_path += ".zip"
        if os.path.exists(output_path):
            if not messagebox.askyesno(
                    "Overwrite?", f"{output_path}\n\nalready exists. Replace it?"):
                return

        level = int(round(self.level_var.get()))
        total_size = get_total_size(self.selected_paths)  # quick size scan

        self._set_busy(True, f"Compressing {len(self.selected_paths)} item(s)...")
        threading.Thread(
            target=self._compression_worker,
            args=(list(self.selected_paths), output_path, level, total_size),
            daemon=True,
        ).start()

    def start_extraction(self):
        zip_path = filedialog.askopenfilename(
            title="Choose a .zip file to extract",
            filetypes=[("Zip archive", "*.zip"), ("All files", "*.*")])
        if not zip_path:
            return
        destination = filedialog.askdirectory(
            title="Choose a folder to extract into")
        if not destination:
            return
        self._set_busy(True, "Extracting...")
        threading.Thread(
            target=self._extraction_worker, args=(zip_path, destination),
            daemon=True,
        ).start()

    # ==================================================================
    # PART 4: WORKERS (background threads - NEVER touch widgets here!)
    #
    # These run OUTSIDE the GUI thread. tkinter widgets would crash if
    # we touched them from here, so we only do two things:
    #   1. the actual compression/extraction work
    #   2. drop messages into the queue.Queue "mailbox"
    # ==================================================================
    def _compression_worker(self, paths, output_path, level, total_size):
        try:
            compress_to_zip(
                paths, output_path, level,
                # This tiny lambda turns each "file done" event into a
                # mailbox message the GUI thread will pick up later.
                progress_callback=lambda done, total:
                    self.message_queue.put(("progress", done, total)),
            )
            compressed_size = os.path.getsize(output_path)
            self.message_queue.put(
                ("compress_done", output_path, total_size, compressed_size))
        except Exception as error:
            # Broad except on purpose: whatever goes wrong (bad path,
            # locked file...), we want it shown nicely in the GUI.
            self.message_queue.put(("error", f"Compression failed:\n{error}"))

    def _extraction_worker(self, zip_path, destination):
        try:
            count = extract_zip(
                zip_path, destination,
                progress_callback=lambda done, total:
                    self.message_queue.put(("progress", done, total)),
            )
            self.message_queue.put(("extract_done", zip_path, destination, count))
        except Exception as error:
            self.message_queue.put(("error", f"Extraction failed:\n{error}"))

    # ==================================================================
    # PART 5: READ THE MAILBOX (GUI thread, 10 times per second)
    #
    # root.after(100, ...) schedules this method to run again in 100 ms
    # forever - that's how the GUI notices what the worker did.
    # ==================================================================
    def _poll_queue(self):
        try:
            while True:  # drain every message that arrived since last check
                self._handle_message(self.message_queue.get_nowait())
        except queue.Empty:
            pass  # mailbox empty - nothing to do this round
        self.root.after(100, self._poll_queue)  # check again in 100 ms

    def _handle_message(self, message):
        kind = message[0]
        if kind == "progress":
            _, done, total = message
            percent = int(done / total * 100) if total else 100
            self.progress["value"] = percent
            self.status_label.config(
                text=f"Working... {done}/{total} files ({percent}%)")
        elif kind == "compress_done":
            _, output_path, original, compressed = message
            self.progress["value"] = 100
            saved = max(original - compressed, 0)
            percent_saved = saved / original * 100 if original else 0
            self._set_busy(False, "Done!")
            self._log(
                f"[OK] Compressed -> {output_path}\n"
                f"     Original : {format_size(original)}\n"
                f"     Zipped   : {format_size(compressed)}\n"
                f"     Saved    : {format_size(saved)} "
                f"({percent_saved:.1f}% smaller)\n")
            messagebox.showinfo("Success", f"Archive saved to:\n{output_path}")
        elif kind == "extract_done":
            _, zip_path, destination, count = message
            self.progress["value"] = 100
            self._set_busy(False, "Done!")
            self._log(
                f"[OK] Extracted {count} item(s)\n"
                f"     From : {zip_path}\n"
                f"     Into : {destination}\n")
            messagebox.showinfo(
                "Success", f"Extracted {count} item(s) to:\n{destination}")
        elif kind == "error":
            self._set_busy(False, "Something went wrong.")
            self._log(f"[ERROR] {message[1]}\n")
            messagebox.showerror("Error", message[1])