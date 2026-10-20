
import gzip
import os

# The file we want to compress
input_file = "sample.txt"

# The name of the compressed file
output_file = "sample.txt.gz"

# Open the original file and read its contents
with open(input_file, "rb") as file:
    data = file.read()

# Compress the file contents
compressed_data = gzip.compress(data)

# Save the compressed contents
with open(output_file, "wb") as file:
    file.write(compressed_data)

# Compare the original and compressed sizes
original_size = os.path.getsize(input_file)
compressed_size = os.path.getsize(output_file)

print("Compression complete!")
print("Original size:", original_size, "bytes")
print("Compressed size:", compressed_size, "bytes")

if compressed_size < original_size:
    saved = original_size - compressed_size
    percentage = (saved / original_size) * 100
    print("Space saved:", round(percentage, 2), "%")
else:
    print("The compressed file is not smaller this time.")
