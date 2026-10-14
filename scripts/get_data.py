"""
Download and extract the Apache SpamAssassin public email corpus.

Source: https://spamassassin.apache.org/old/publiccorpus/
License: Apache SpamAssassin Public Corpus - public domain / freely available
         Individual emails may have varied original licenses.

Downloads:
  - 20030228_easy_ham.tar.bz2   (ham - easy to classify)
  - 20030228_easy_ham_2.tar.bz2 (ham - easy to classify, second batch)
  - 20030228_hard_ham.tar.bz2   (ham - harder to classify)
  - 20030228_spam.tar.bz2       (spam)
  - 20030228_spam_2.tar.bz2     (spam - second batch)
"""

import os
import sys
import tarfile
import urllib.request

BASE_URL = "https://spamassassin.apache.org/old/publiccorpus/"

FILES = [
    ("20030228_easy_ham.tar.bz2", "ham"),
    ("20030228_easy_ham_2.tar.bz2", "ham"),
    ("20030228_hard_ham.tar.bz2", "ham"),
    ("20030228_spam.tar.bz2", "spam"),
    ("20030228_spam_2.tar.bz2", "spam"),
]

# Project root (one level up from scripts/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
DOWNLOAD_DIR = os.path.join(DATA_DIR, "downloads")


def download_file(url, dest_path):
    """Download a file with progress reporting."""
    if os.path.exists(dest_path):
        print(f"  Already downloaded: {os.path.basename(dest_path)}")
        return

    print(f"  Downloading: {url}")
    try:
        urllib.request.urlretrieve(url, dest_path)
        size_mb = os.path.getsize(dest_path) / (1024 * 1024)
        print(f"  Downloaded: {size_mb:.1f} MB")
    except Exception as e:
        print(f"  ERROR downloading {url}: {e}")
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise


def extract_tar_bz2(archive_path, extract_to, label):
    """Extract a .tar.bz2 archive into label-specific directories."""
    print(f"  Extracting: {os.path.basename(archive_path)} -> {label}/")
    label_dir = os.path.join(extract_to, label)
    os.makedirs(label_dir, exist_ok=True)

    with tarfile.open(archive_path, "r:bz2") as tar:
        # Extract all members
        members = tar.getmembers()
        file_count = 0
        for member in members:
            if member.isfile():
                # Flatten directory structure: extract just the filename
                filename = os.path.basename(member.name)
                if filename.startswith("cmds") or filename.startswith("."):
                    continue  # Skip index/hidden files

                # Create unique name to avoid collisions across archives
                archive_prefix = os.path.basename(archive_path).replace(".tar.bz2", "")
                unique_name = f"{archive_prefix}_{filename}"
                dest_path = os.path.join(label_dir, unique_name)

                # Extract file content
                f = tar.extractfile(member)
                if f is not None:
                    with open(dest_path, "wb") as out:
                        out.write(f.read())
                    file_count += 1

        print(f"  Extracted {file_count} files into {label}/")


def main():
    print("=" * 60)
    print("SpamGuard AI — Dataset Download")
    print("Source: Apache SpamAssassin Public Corpus")
    print("=" * 60)

    # Create directories
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)

    # Download all archives
    print("\n--- Step 1: Download archives ---")
    for filename, label in FILES:
        url = BASE_URL + filename
        dest = os.path.join(DOWNLOAD_DIR, filename)
        download_file(url, dest)

    # Extract all archives
    print("\n--- Step 2: Extract archives ---")
    for filename, label in FILES:
        archive_path = os.path.join(DOWNLOAD_DIR, filename)
        extract_tar_bz2(archive_path, RAW_DIR, label)

    # Count results
    print("\n--- Summary ---")
    for label in ["ham", "spam"]:
        label_dir = os.path.join(RAW_DIR, label)
        if os.path.exists(label_dir):
            count = len([f for f in os.listdir(label_dir) if os.path.isfile(os.path.join(label_dir, f))])
            print(f"  {label}: {count} emails")

    print("\nDataset download complete!")
    print(f"Raw data location: {RAW_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
