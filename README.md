
# Fly DB Backup

A python3 application which take backup of `postgres` database and store snapshot to `cloudflare` R2 (S3 equivalent)

## Environment Variables

To run this project, you will need to add the following environment variables to your .env file

- `FLY_API_TOKEN` - API token to comunicate with [fly.io](https://fly.io)
- `APP_NAME` - Fly Application name.
- `PGPASSWORD` - DB password 
- `R2_ACCOUNT_ID` - R2 Account Id 
- `R2_ACCESS_ID` - R2 Access Id, equivalent to `AWS_ACCESS_ID`
- `R2_ACCESS_SECRET` - R2 Access secret, equivalent to `AWS_ACCESS_SECRET`
- `R2_BUCKET_NAME` - R2 bucket name.

Please set these as Github Workflow actions secrets to run the Workflow with cronjob (on github Workflow)

## Badges


[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)

[![.github/workflows/backup.yml](https://github.com/shubham399/fly_db_backup/actions/workflows/backup.yml/badge.svg)](https://github.com/shubham399/fly_db_backup/actions/workflows/backup.yml)
