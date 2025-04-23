import os
import sh
import time
import boto3
import requests
import logging
import sys
from datetime import datetime

# --- Configuration ---
# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Required environment variables
R2_ACCOUNT_ID = os.getenv('R2_ACCOUNT_ID')
R2_ACCESS_ID = os.getenv('R2_ACCESS_ID')
R2_ACCESS_SECRET = os.getenv('R2_ACCESS_SECRET')
APP_NAME = os.getenv("APP_NAME")
PGPASSWORD = os.getenv("PGPASSWORD")

# Optional environment variables
R2_BUCKET_NAME = os.getenv('R2_BUCKET_NAME', default="my-bucket")
UPTIME_HEARTBEAT_URL = os.getenv('UPTIME_HEARTBEAT')

# Default backup parameters (can be overridden)
DEFAULT_DB_NAME = "postgres"
DEFAULT_DB_USER = "postgres"
DEFAULT_DB_HOST = "localhost"
DEFAULT_PROXY_PORT = 5499
DEFAULT_DB_PORT = 5432 # The actual DB port inside the Fly network

# --- Validate Configuration ---
required_vars = {
    "R2_ACCOUNT_ID": R2_ACCOUNT_ID,
    "R2_ACCESS_ID": R2_ACCESS_ID,
    "R2_ACCESS_SECRET": R2_ACCESS_SECRET,
    "APP_NAME": APP_NAME,
    "PGPASSWORD": PGPASSWORD,
}

missing_vars = [name for name, value in required_vars.items() if not value]
if missing_vars:
    logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

# --- S3 Client Setup ---
try:
    endpoint_url = f'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com'
    s3 = boto3.resource('s3',
                        endpoint_url=endpoint_url,
                        aws_access_key_id=R2_ACCESS_ID,
                        aws_secret_access_key=R2_ACCESS_SECRET
                        )
    # Test connection by listing buckets (optional, requires ListBuckets permission)
    # s3.meta.client.list_buckets()
    logging.info(f"Successfully configured S3 client for bucket: {R2_BUCKET_NAME}")
except Exception as e:
    logging.error(f"Failed to configure S3 client: {e}")
    sys.exit(1)


def fly_db_connect(app_name, local_port=DEFAULT_PROXY_PORT, remote_port=DEFAULT_DB_PORT):
    """
    Establishes a background proxy connection to the Fly database.
    Returns the running process handle.
    """
    logging.info(f"Attempting to start flyctl proxy for app '{app_name}' ({local_port}:{remote_port})...")
    try:
        # Run flyctl proxy in the background (_bg=True)
        # Redirect stdout/stderr to avoid clutter, log separately if needed
        process = sh.flyctl(
            "proxy", f"{local_port}:{remote_port}",
            "--app", app_name,
            _bg=True,
            _bg_exc=False, # Don't raise exception immediately on background error
            # _out=logging.info, # Uncomment to log flyctl output
            # _err=logging.warning # Uncomment to log flyctl errors
        )
        logging.info(f"flyctl proxy process started (PID: {process.pid}). Waiting for connection...")
        # Give the proxy time to establish connection
        time.sleep(5) # Increased sleep time slightly
        # Check if the background process is still running
        if not process.is_alive():
             logging.error("flyctl proxy process failed to start or terminated unexpectedly.")
             # Attempt to get error output if possible (might not work reliably with _bg)
             try:
                 stderr_output = process.stderr.decode()
                 logging.error(f"flyctl proxy stderr: {stderr_output}")
             except Exception:
                 pass # Ignore if stderr cannot be read
             return None
        logging.info("flyctl proxy seems to be running.")
        return True
    except sh.CommandNotFound:
        logging.error("`flyctl` command not found. Make sure it's installed and in your PATH.")
        return None
    except sh.ErrorReturnCode as e:
        logging.error(f"Failed to start flyctl proxy: {e}")
        logging.error(f"Stdout: {e.stdout.decode()}")
        logging.error(f"Stderr: {e.stderr.decode()}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred while starting flyctl proxy: {e}")
        return None


def upload_to_s3(local_filename, s3_key):
    """Uploads a file to the configured S3 bucket."""
    logging.info(f"Uploading '{local_filename}' to S3 bucket '{R2_BUCKET_NAME}' as '{s3_key}'...")
    try:
        s3.meta.client.upload_file(local_filename, R2_BUCKET_NAME, s3_key)
        logging.info("Upload successful.")
        return True
    except boto3.exceptions.S3UploadFailedError as e:
        logging.error(f"S3 upload failed: {e}")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred during S3 upload: {e}")
        return False

def send_heartbeat(url):
    """Sends a GET request to the specified heartbeat URL."""
    if not url:
        logging.info("No heartbeat URL configured. Skipping.")
        return
    logging.info(f"Sending heartbeat to {url}...")
    try:
        response = requests.get(url, timeout=10) # Add a timeout
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        logging.info(f"Heartbeat sent successfully (Status: {response.status_code}).")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to send heartbeat: {e}")


def fly_db_backup(
    app_name,
    db_password,
    db_name=DEFAULT_DB_NAME,
    db_user=DEFAULT_DB_USER,
    db_host=DEFAULT_DB_HOST,
    proxy_port=DEFAULT_PROXY_PORT,
):
    """Connects to fly.io via proxy, backs up the database, and uploads to S3."""
    logging.info(f"Starting database backup for app '{app_name}', database '{db_name}'.")
    start_time = time.time()
    db_connection = None # Handle for the flyctl proxy process

    try:
        # 1. Start the proxy connection
        db_connection = fly_db_connect(app_name=app_name, local_port=proxy_port)
        print(f"🔍 ~  ~ backup.py:150 ~ {db_connection}:")
        if not db_connection:
            # Error already logged in fly_db_connect
            logging.error("Backup failed due to proxy connection error.")
            return # Exit if proxy failed

        # 2. Create backup directory
        logging.info("Ensuring backup directory exists...")
        backup_dir = f"{app_name}_backup"
        try:
            # Use os.makedirs for potentially nested directories and exist_ok=True
            os.makedirs(backup_dir, exist_ok=True)
            logging.info(f"Backup directory '{backup_dir}' ensured.")
        except OSError as e:
            logging.error(f"Failed to create backup directory '{backup_dir}': {e}")
            return # Cannot proceed without backup directory

        # 3. Define backup filename
        logging.info("Generating backup filename...")
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") # ISO-like format, better for sorting
        base_filename = f"{db_name}-backup-{current_time}.sql"
        local_backup_path = os.path.join(backup_dir, base_filename)
        s3_key = f"{app_name}/{base_filename}" # Store under app_name prefix in S3

        logging.info(f"Starting pg_dump to '{local_backup_path}'...")

        # 4. Execute pg_dump
        try:
            # Use PGPASSWORD environment variable implicitly (preferred by pg_dump)
            # Or pass via _in if needed, but env var is standard
            process = sh.pg_dump(
                "--host", db_host,
                "--port", proxy_port,
                "--username", db_user,
                "-F", "p",
                "-b", 
                "-v",
                "--file", local_backup_path,
                db_name,
                _out=sys.stdout, # Stream pg_dump output if needed
                _err=sys.stderr, # Stream pg_dump errors
                # _in=db_password, # Use if PGPASSWORD env var isn't set/preferred
                _env={**os.environ, "PGPASSWORD": db_password} # Ensure PGPASSWORD is set for the command
            )
            # pg_dump with -f writes to file, output might be minimal unless verbose options are used
            logging.info(f"pg_dump completed successfully.")

        except sh.ErrorReturnCode as e:
            logging.error(f"pg_dump failed with exit code {e.exit_code}.")
            logging.error(f"Stdout: {e.stdout.decode()}")
            logging.error(f"Stderr: {e.stderr.decode()}")
            # Optionally remove the potentially incomplete backup file
            if os.path.exists(local_backup_path):
                try:
                    os.remove(local_backup_path)
                    logging.info(f"Removed incomplete backup file: {local_backup_path}")
                except OSError as remove_err:
                    logging.warning(f"Could not remove incomplete backup file '{local_backup_path}': {remove_err}")
            return # Stop process if dump failed
        except sh.CommandNotFound:
            logging.error("`pg_dump` command not found. Make sure PostgreSQL client tools are installed.")
            return

        # 5. Upload to S3
        if not upload_to_s3(local_backup_path, s3_key):
            # Error logged in upload_to_s3
            logging.error(f"Backup failed due to S3 upload error. Local file kept at '{local_backup_path}'.")
            # Fail fast: Exit the backup function if upload fails
            return # <-- ADDED RETURN HERE
        else:
             # 6. Remove local backup file after successful upload (optional)
             try:
                 os.remove(local_backup_path)
                 logging.info(f"Removed local backup file: {local_backup_path}")
             except OSError as e:
                 logging.warning(f"Could not remove local backup file '{local_backup_path}': {e}")


        # 7. Send Heartbeat (Only runs if pg_dump and upload succeed)
        send_heartbeat(UPTIME_HEARTBEAT_URL)

    except Exception as e:
        # Catch any unexpected errors during the main backup logic
        logging.exception(f"An unexpected error occurred during the backup process: {e}")
    finally:

        end_time = time.time()
        logging.info(f"Backup process finished. Total runtime: {end_time - start_time:.2f} seconds.")


# --- Main Execution ---
if __name__ == "__main__":
    # Run the backup with environment variables
    fly_db_backup(
        app_name=APP_NAME,
        db_password=PGPASSWORD,
        # Optional overrides can be added here if needed
        # db_name="custom_db_name",
        # db_user="custom_user",
        # db_host="custom_host",
        # proxy_port=5434,
    )
