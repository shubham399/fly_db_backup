import os
import sh
import time
import boto3
import requests
from datetime import datetime

account_id = os.getenv('R2_ACCOUNT_ID')
bucket_name = os.getenv('R2_BUCKET_NAME', default="my-bucket")
if not account_id:
    print("ERROR: R2_ACCOUNT_ID not passed")
    exit(1)

endpoint_url = f'https://{account_id}.r2.cloudflarestorage.com'

s3 = boto3.resource('s3',
                    endpoint_url=endpoint_url,
                    aws_access_key_id=os.getenv('R2_ACCESS_ID'),
                    aws_secret_access_key=os.getenv('R2_ACCESS_SECRET')
                    )


def fly_db_connect(app_name="app-name", bg: int = 0):
    """
    Connect to the database
    :param app_name: The name of the app
    :param bg: Run in the background (0-false, 1-true)
    """
    print(f"[green]Connecting to {app_name}, {bg}")
    _bg = bg == 1
    print(
        f"[green]Connecting to the database: Running in the background: {_bg}")
    try:
        return sh.flyctl("proxy", "5433:5432", app=app_name, _out=print, _bg=_bg)
    except sh.ErrorReturnCode as e:
        print(e)


def fly_db_backup(
    password=None,
    port=5433,
    user="postgres",
    host="localhost",
    db_name="public",
    app_name=None,
):
    """Connect to fly.io and backup the database"""
    password = os.getenv("PGPASSWORD", default=password)
    app_name = os.getenv("APP_NAME", default=app_name)
    if not app_name or not password:
        print("ERROR: app_name or password is empty or not set in the environment.")
        exit(1)
    db_connection = None
    try:
        print("[green] Backing up the database")
        # start timer
        start = time.time()
        db_connection = fly_db_connect(app_name=app_name, bg=1)
        # wait for the connection here
        time.sleep(3)
        sh.mkdir("-p", f"{app_name}_backup")
        current_time = datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
        filename = f"{app_name}_backup/{db_name}-backup-{current_time}.sql"
        print(f"[green]Backing up the database to {filename}, please wait...")
        process = sh.pg_dump(
            "-h",
            host,
            "-p",
            port,
            "-U",
            user,
            "-f",
            filename,
            db_name,
            _out=print,
            _in=password,
            _bg=False,
        )
        print(process)

        print("[green] backup complete, uploading to sq")
        upload_file(filename)
        heartbeat_url = os.getenv('UPTIME_HEARTBEAT')
        if heartbeat_url:
            requests.get(url=heartbeat_url)
        # end timer
        end = time.time()
        print(f"[green] Total runtime of the program is [red] {end - start}")
        db_connection.terminate()

    except sh.ErrorReturnCode as e:
        print(e)
        if db_connection:
            db_connection.terminate()


def upload_file(filename):
    print("Uploading backup to S3")
    s3.meta.client.upload_file(filename, bucket_name, filename)

print("Backuping up DB")
fly_db_backup(
    password=None,
    db_name="postgres",
    port=5433,
    user="postgres",
    host="localhost",
    app_name=None
)
