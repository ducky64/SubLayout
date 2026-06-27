import argparse
import os
import json
import hashlib
import zipfile


def zip_uncompressed_size(filepath: str) -> int:
    with zipfile.ZipFile(filepath, 'r') as archive:
        return sum(zinfo.file_size for zinfo in archive.infolist())


def calculate_sha256(filepath: str) -> str:
    """Calculate the SHA256 checksum of a file in binary chunks."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add release metadata to the KiCad metadata.json file, in-place. "
                                     "Release data (URL, package metadata) is added to the first version in the versions list, other versions are left unmodified.")
    parser.add_argument("metadata_json", type=str, help="Metadata .json file, modified in-place, must contain all entries except for package metadata")
    parser.add_argument("--url", type=str, default="", help="Package download URL")
    parser.add_argument("--package", type=str, default="", help="Optional package .zip file, otherwise package metadata omitted")
    parser.add_argument("--version", type=str, default="", help="Optional version string to set the first version entry, otherwise left unmodified")
    args = parser.parse_args()

    with open(args.metadata_json, "r") as f:
        metadata = json.load(f)

    assert "versions" in metadata and isinstance(metadata["versions"], list) and len(metadata["versions"]) > 0, \
        "Requires a placeholder version entry to add release metadata to"
    version_block = metadata["versions"][0]

    if args.url:
        version_block["download_url"] = args.url

    if args.package:
        version_block["download_sha256"] = calculate_sha256(args.package)
        version_block["download_size"] = os.path.getsize(args.package)
        version_block["install_size"] = zip_uncompressed_size(args.package)

    if args.version:
        version_block["version"] = args.version

    with open(args.metadata_json, "w") as f:
        json.dump(metadata, f, indent=2)
