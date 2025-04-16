 # Fly DB Backup

A Python 3 application that automates the backup of a PostgreSQL database and stores the snapshot in Cloudflare R2 (an S3-equivalent object storage service).


## Features

- **Automated Backups**: Seamlessly backs up your PostgreSQL database.
- **Cloudflare R2 Integration**: Store database snapshots in Cloudflare R2.
- **Scheduled Backups**: Supports scheduled backups using GitHub Actions.
- **Uptime Monitoring**: (Optional) Integrate with a heartbeat service to monitor backup completion.

## Prerequisites

- **Python 3.6+**
- PostgreSQL database
- Cloudflare R2 account

## Environment Variables

To run this project, you will need to add the following environment variables to your `.env` file:

| Variable             | Description                                            |
|----------------------|--------------------------------------------------------|
| `FLY_API_TOKEN`       | API token to communicate with [fly.io](https://fly.io) |
| `APP_NAME`           | Fly application name (typically the database name)     |
| `PGPASSWORD`         | PostgreSQL database password                           |
| `R2_ACCOUNT_ID`      | Cloudflare R2 account ID                               |
| `R2_ACCESS_ID`       | Cloudflare R2 access key (equivalent to AWS access key)|
| `R2_ACCESS_SECRET`   | Cloudflare R2 secret key (equivalent to AWS secret key)|
| `R2_BUCKET_NAME`     | Cloudflare R2 bucket name                              |
| `UPTIME_HEARTBEAT`   | *(Optional)* URL to send a GET request upon completion of the backup workflow |

### GitHub Actions Integration

To automate backups with GitHub Actions, set these environment variables as GitHub Actions secrets and configure a cron job in your GitHub Workflow.

## Usage

1. Clone this repository.
2. Install required dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3. Create a `.env` file in the project root and configure the environment variables as described above.
4. Run the backup script manually:
    ```bash
    python backup.py
    ```
5. To automate backups, configure your GitHub Actions workflow with a cron schedule.

## Badges

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)  
[![Backup Workflow](https://github.com/shubham399/fly_db_backup/actions/workflows/backup.yml/badge.svg)](https://github.com/shubham399/fly_db_backup/actions/workflows/backup.yml)

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
