#!/bin/bash
###############################################################################
# BOM检查系统 - 轻量更新脚本
# 用途：代码 push 后在服务器上执行增量更新并重启服务
# 使用：sudo bash deploy/scripts/deploy_update.sh
###############################################################################

set -euo pipefail

APP_NAME="bom_check"
APP_DIR="/opt/${APP_NAME}"
APP_USER="bomuser"
VENV_PYTHON="${APP_DIR}/venv/bin/python"
BRANCH="${DEPLOY_BRANCH:-master}"

log() {
    echo "[deploy_update] $1"
}

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        echo "This script must be run as root." >&2
        exit 1
    fi
}

require_paths() {
    if [[ ! -d "${APP_DIR}" ]]; then
        echo "Application directory not found: ${APP_DIR}" >&2
        exit 1
    fi

    if [[ ! -x "${VENV_PYTHON}" ]]; then
        echo "Virtualenv python not found: ${VENV_PYTHON}" >&2
        exit 1
    fi
}

run_as_app_user() {
    sudo -u "${APP_USER}" bash -lc "cd '${APP_DIR}' && $1"
}

update_code() {
    log "Updating code from branch ${BRANCH}"
    run_as_app_user "git fetch origin '${BRANCH}' && git checkout '${BRANCH}' && git pull --ff-only origin '${BRANCH}'"
}

install_python_deps() {
    log "Installing Python dependencies"
    run_as_app_user "'${VENV_PYTHON}' -m pip install --upgrade pip setuptools wheel && '${VENV_PYTHON}' -m pip install -r requirements-prod.txt"
}

ensure_runtime_dirs() {
    log "Ensuring runtime directories and permissions"
    mkdir -p "${APP_DIR}/logs" "${APP_DIR}/reports" "${APP_DIR}/temp/uploads"
    chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
    chmod 600 "${APP_DIR}/.env"
}

install_systemd_units() {
    log "Updating systemd unit files"
    cp "${APP_DIR}/deploy/systemd/bom-api.service" /etc/systemd/system/bom-api.service
    cp "${APP_DIR}/deploy/systemd/bom-sync.service" /etc/systemd/system/bom-sync.service
    cp "${APP_DIR}/deploy/systemd/bom-sync.timer" /etc/systemd/system/bom-sync.timer
}

reload_services() {
    install_systemd_units

    log "Reloading systemd configuration"
    systemctl daemon-reload

    log "Restarting bom-api service"
    systemctl restart bom-api

    if systemctl list-unit-files | grep -q '^bom-sync.timer'; then
        log "Ensuring bom-sync timer is running"
        systemctl enable bom-sync.timer >/dev/null 2>&1 || true
        systemctl restart bom-sync.timer
    fi
}

show_status() {
    log "Deployment completed"
    systemctl --no-pager --full status bom-api || true
}

main() {
    require_root
    require_paths
    update_code
    install_python_deps
    ensure_runtime_dirs
    reload_services
    show_status
}

main "$@"
