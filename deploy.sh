#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# 一键部署脚本 — 到期提醒监控系统
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${SCRIPT_DIR}/data"
DEFAULT_PORT=5188

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

check_prerequisites() {
    local missing=()
    if ! command -v docker &>/dev/null; then missing+=("docker"); fi
    if ! docker compose version &>/dev/null 2>&1 && ! docker-compose version &>/dev/null 2>&1; then missing+=("docker-compose"); fi
    if [[ ${#missing[@]} -gt 0 ]]; then
        error "Missing dependencies: ${missing[*]}"
        exit 1
    fi
}

init_data_dir() {
    mkdir -p "${DATA_DIR}"
    if [[ ! -f "${DATA_DIR}/certs.json" ]]; then
        echo '[]' > "${DATA_DIR}/certs.json"
        info "Created ${DATA_DIR}/certs.json"
    fi
    if [[ ! -f "${DATA_DIR}/config.json" ]]; then
        cat > "${DATA_DIR}/config.json" << 'CFGEOF'
{
  "webhook_url": "",
  "secret": "",
  "remind_days": [30, 14, 7, 3, 1],
  "email_enabled": false,
  "smtp_host": "",
  "smtp_port": 465,
  "smtp_user": "",
  "smtp_pass": "",
  "smtp_to": "",
  "smtp_from_name": "Certificate Monitor",
  "wecom_enabled": false,
  "wecom_webhook": ""
}
CFGEOF
        info "Created ${DATA_DIR}/config.json"
    fi
    if [[ ! -f "${DATA_DIR}/users.json" ]]; then
        INIT_PASS=$(openssl rand -base64 12 2>/dev/null || echo "admin123")
        cat > "${DATA_DIR}/users.json" << USREOF
[
  {
    "username": "admin",
    "name": "Administrator",
    "password": "${INIT_PASS}",
    "dingtalk_id": "",
    "role": "admin",
    "failed_attempts": 0,
    "consecutive_locks": 0,
    "lock_until": null
  }
]
USREOF
        info "Created ${DATA_DIR}/users.json (initial password: ${INIT_PASS})"
    fi
    if [[ ! -f "${DATA_DIR}/logs.json" ]]; then
        echo '[]' > "${DATA_DIR}/logs.json"
        info "Created ${DATA_DIR}/logs.json"
    fi
    if [[ ! -f "${DATA_DIR}/remind_state.json" ]]; then
        echo '{}' > "${DATA_DIR}/remind_state.json"
        info "Created ${DATA_DIR}/remind_state.json"
    fi
}

main() {
    echo ""
    echo "=========================================="
    echo "  Certificate Monitor - One-Click Deploy"
    echo "=========================================="
    echo ""
    check_prerequisites
    if [[ -f "${DATA_DIR}/.secret_key" ]]; then
        info "Existing deployment detected, skipping initialization"
    else
        info "Initializing data directory..."
        init_data_dir
    fi
    info "Building Docker image..."
    cd "${SCRIPT_DIR}"
    if docker compose version &>/dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    ${COMPOSE_CMD} build --pull
    ${COMPOSE_CMD} up -d
    echo ""
    info "Deployment complete!"
    info "Access URL: http://localhost:${DEFAULT_PORT}"
    info "Default account: admin"
    echo ""
    info "View logs: ${COMPOSE_CMD} logs -f"
    echo ""
}

main "$@"
