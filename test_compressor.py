"""
test_compressor.py - Automated test for the compression engine.

It builds a temporary sandbox with some files, compresses them,
extracts the archive again, and verifies nothing was lost.
That's called a "round-trip test" - a very useful habit!

Run it with:   python test_compressor.py
"""

import os
import shutil
import tempfile
import zipfile

from compressor import compress_to_zip, extract_zip, format_size, get_total_size


def run_test():
    # tempfile.mkdtemp gives us a fresh throwaway folder - polite,
    # because we never scatter test junk into your real folders.
    sandbox = tempfile.mkdtemp(prefix="compressor_test_")
    try:
        # 1. Create files to compress. Repeated text compresses very well.
        source = os.path.join(sandbox, "source")
        os.makedirs(source)
        text = "Hello from the PyCompressor test! " * 500
        for i in range(3):
            with open(os.path.join(source, f"note_{i}.txt"), "w", encoding="utf-8") as f:
                f.write(f"File number {i}\n" + text)

        # A subfolder too, so we test that folder structure survives.
        os.makedirs(os.path.join(source, "subfolder"))
        with open(os.path.join(source, "subfolder", "deep.txt"), "w", encoding="utf-8") as f:
            f.write(text)

        # 2. Compress.
        total_size = get_total_size([source])
        zip_path = os.path.join(sandbox, "out.zip")
        compress_to_zip([source], zip_path, compression_level=9)
        zipped_size = os.path.getsize(zip_path)
        print(f"Original: {format_size(total_size)} -> Zipped: {format_size(zipped_size)}")
        assert zipped_size < total_size, "the zip should be smaller!"

        # 3. Extract and verify the files came back identical.
        out_dir = os.path.join(sandbox, "extracted")
        count = extract_zip(zip_path, out_dir)
        print(f"Extracted {count} items")
        with open(os.path.join(source, "note_1.txt"), encoding="utf-8") as f:
            original_text = f.read()
        restored = os.path.join(out_dir, "source", "note_1.txt")
        with open(restored, encoding="utf-8") as f:
            assert f.read() == original_text, "file content changed!"

        deep = os.path.join(out_dir, "source", "subfolder", "deep.txt")
        assert os.path.isfile(deep), "subfolder structure was lost!"

        with zipfile.ZipFile(zip_path) as zf:
            print("Names inside the zip:", zf.namelist())

        print("ALL TESTS PASSED")
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)


if __name__ == "__main__":
    run_test()