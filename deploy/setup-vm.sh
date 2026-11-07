#!/bin/sh
# One-time setup of the Azure VM (Ubuntu 24.04, B1s) for RiceFlow. Run it once as the VM's
# admin user:   sudo sh setup-vm.sh
#
# Installs Docker, adds 2 GB of swap (B1s has only 1 GB of memory), opens only the SSH and
# web ports, makes /opt/riceflow, and backs up the database every night (7 days kept).
set -e

APP_DIR=/opt/riceflow
ADMIN_USER="${SUDO_USER:-$(id -un)}"

echo "== Docker"
apt-get update -y
apt-get install -y docker.io docker-compose-v2 ufw
systemctl enable --now docker
usermod -aG docker "$ADMIN_USER"     # takes effect at the next login

echo "== 2 GB swap"
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "== Firewall: SSH, HTTP, HTTPS only"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "== App folder"
mkdir -p "$APP_DIR/data" "$APP_DIR/backups"
chown -R "$ADMIN_USER" "$APP_DIR"

echo "== Nightly database backup at 2 AM (7 days kept)"
cat > /etc/cron.d/riceflow-backup <<EOF
0 2 * * * $ADMIN_USER cd $APP_DIR && docker compose -f docker-compose.prod.yml exec -T db sh -c 'pg_dump -U \$POSTGRES_USER \$POSTGRES_DB | gzip > /backups/riceflow-\$(date +\%F).sql.gz' && find $APP_DIR/backups -name 'riceflow-*.sql.gz' -mtime +7 -delete
EOF

echo "Done. Log out and back in once so Docker works without sudo."
