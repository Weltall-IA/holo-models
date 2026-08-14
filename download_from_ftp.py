"""
Download all files from a specific directory on an FTP server using wget in a subprocess.
"""

import subprocess
import os
import sys
from typing import List


def download_files_from_ftp(
    ftp_server: str = "ftp.dlptest.com",
    ftp_user: str = "dlpuser",
    ftp_password: str = "rNrKYTX9g7z3RgJRmxWuGHbeu",
    ftp_dir: str = "/ftp/test",
) -> List[str]:
    """Download all files from a specific directory on an FTP server using wget.

    Args:
        ftp_server: The FTP server address. Default is 'ftp.dlptest.com'.
        ftp_user: The FTP server username. Default is 'dlpuser'.
        ftp_password: The FTP server password. Default is 'rNrKYTX9g7z3RgJRmxWuGHbeu'.
        ftp_dir: The directory path on the FTP server from which files need to be downloaded.
            Default is '/ftp/test'.

    Raises:
        Exception: If there is a failure in connecting to the FTP server.
            Outputs the message 'Failed to connect to FTP server {ftp_server}: {str(e)}'.
        Exception: If there is a failure in logging into the FTP server.
            Outputs the message 'Failed to log into FTP server {ftp_server} with user {ftp_user}: {str(e)}'.
        Exception: If there is a failure in changing to the specified directory.
            Outputs the message 'Failed to change to directory {ftp_dir} on server {ftp_server}: {str(e)}'.

    Returns:
        A list of filenames that were attempted to be downloaded from the FTP server.
    """
    downloaded_files: List[str] = []

    # Create a local directory to store downloaded files
    local_dir = "ftp_downloads"
    os.makedirs(local_dir, exist_ok=True)

    # Step 1: Connect to FTP server and list directory contents
    # Build the FTP URL with credentials
    ftp_url = f"ftp://{ftp_user}:{ftp_password}@{ftp_server}"

    # First, try to list files using wget with spider mode
    try:
        # Attempt to get file listing by making a request to the FTP directory
        result = subprocess.run(
            [
                "wget",
                "-O-",
                "--spider",
                "-U",
                f"{ftp_url}{ftp_dir}",
                "--level=0",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        raise Exception(
            f"Failed to connect to FTP server {ftp_server}: Connection timed out"
        )
    except Exception as e:
        raise Exception(
            f"Failed to connect to FTP server {ftp_server}: {str(e)}"
        )

    # Check if the connection/login succeeded
    if result.returncode != 0:
        raise Exception(
            f"Failed to connect to FTP server {ftp_server}: "
            f"{result.stderr.strip() if result.stderr else result.stdout.strip()}"
        )

    # Check if login succeeded (look for authentication failure indicators)
    output = result.stdout + result.stderr
    if "501" in output or "530" in output or "Login" in output or "denied" in output.lower():
        raise Exception(
            f"Failed to log into FTP server {ftp_server} with user {ftp_user}: "
            f"Authentication failed"
        )

    # Step 2: Extract file list from wget output
    # Parse the directory listing to get filenames
    for line in result.stdout.splitlines():
        line = line.strip()
        if line and (line.startswith("ftp://") or line.startswith("http://")):
            # Extract just the filename from the URL
            filename = line.split("/")[-1]
            if filename and filename not in downloaded_files:
                downloaded_files.append(filename)

    # Step 3: If no files found via spider, try recursive download and collect filenames
    if not downloaded_files:
        try:
            result = subprocess.run(
                [
                    "wget",
                    "-r",
                    "-l",
                    "0",
                    "--no-parent",
                    "-O",
                    local_dir,
                    f"{ftp_url}{ftp_dir}",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                raise Exception(
                    f"Failed to change to directory {ftp_dir} on server {ftp_server}: "
                    f"{result.stderr.strip() if result.stderr else result.stdout.strip()}"
                )

            # Collect downloaded files
            if os.path.exists(local_dir):
                for item in os.listdir(local_dir):
                    full_path = os.path.join(local_dir, item)
                    if os.path.isfile(full_path):
                        downloaded_files.append(item)

        except subprocess.TimeoutExpired:
            raise Exception(
                f"Failed to change to directory {ftp_dir} on server {ftp_server}: "
                "Timeout while accessing directory"
            )
        except Exception as e:
            raise Exception(
                f"Failed to change to directory {ftp_dir} on server {ftp_server}: {str(e)}"
            )

    if not downloaded_files:
        raise Exception(
            f"Failed to change to directory {ftp_dir} on server {ftp_server}: "
            "Directory not found or access denied"
        )

    return downloaded_files


if __name__ == "__main__":
    try:
        files = download_files_from_ftp()
        print(f"Downloaded {len(files)} files:")
        for f in files:
            print(f"  - {f}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
