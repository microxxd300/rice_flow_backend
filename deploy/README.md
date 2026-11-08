# Deploying the RiceFlow backend (Azure VM)

Production: **https://api.riceflow.me** on an Azure for Students VM (B1s, Ubuntu 24.04,
Southeast Asia). Caddy gives it HTTPS; the admin website and landing page are on Vercel.

## One-time setup

1. **DNS (Namecheap):** an `A` record `api` → the VM's public IP.
2. **On the VM:** copy this folder to `/opt/riceflow`, then `sudo sh setup-vm.sh`
   (Docker, 2 GB swap, firewall for 22/80/443, nightly database backup). Log out and in once.
3. **Settings:** `cp .env.prod.example .env.prod` and fill in every `<...>`.
4. **Data files** (not in git) into `/opt/riceflow/data/`:
   `panabo_landcover.npz`, `panabo_buildings.npz` (from `manage.py load_land_data`),
   `panabo_openlandmap.npz` (from `manage.py load_openlandmap`) and `harvests.csv`
   (the DA harvest reports, `YIELD_TRAINING_CSV`).
5. **Start:** `docker compose -f docker-compose.prod.yml up -d`. The first start runs the
   migrations, trains the models, and Caddy gets the HTTPS certificate.
6. **Admin account:** `docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser`.

## Releases (CD)

Merging into `main` runs `.github/workflows/cd.yml`: it builds the image, pushes it to GHCR,
logs into the VM over SSH, pulls it and restarts the backend, then waits for `/api/health/`
to report the new commit. It needs these GitHub settings:

| Name | Kind | Value |
|---|---|---|
| `AZURE_VM_HOST` | secret | the VM's public IP |
| `AZURE_VM_USER` | secret | the VM's admin user |
| `AZURE_VM_SSH_KEY` | secret | the private key used to log into the VM |
| `PRODUCTION_URL` | variable | `https://api.riceflow.me` |

Without `AZURE_VM_HOST` the image is still built and pushed, and the deploy is skipped.

## Backups

Every night at 2 AM the database is saved to `/opt/riceflow/backups/` (7 days kept).
Restore one: `gunzip -c backups/riceflow-YYYY-MM-DD.sql.gz | docker compose -f docker-compose.prod.yml exec -T db psql -U riceflow riceflow`.

At 2:30 AM `upload-backup.sh` copies the newest backup to the private S3 bucket `riceflow-db-backups-2026`
(Sydney, versioning on) and checks that S3 stored the same bytes. Results go to `/opt/riceflow/upload-backup.log`.

On a new VM: copy `upload-backup.sh` to `/opt/riceflow/` (`chmod 700`), create `.aws-backup.env` (mode 600) with
`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`, and add this to the `riceflow` user's crontab:
`30 2 * * * /opt/riceflow/upload-backup.sh >> /opt/riceflow/upload-backup.log 2>&1`.

The key can only upload, so to restore from S3 download the file in the AWS console and copy it to `backups/`.
The AWS free plan ends on 2027-05-08: move the backups off it before then.
