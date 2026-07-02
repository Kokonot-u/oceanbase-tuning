#!/bin/bash

###############################################################################
# OceanBase 快捷操作脚本
#
# 支持以下命令：
#   start   - 启动容器 + 启动OB集群
#   stop    - 优雅停止OB集群 + 停止容器
#   status  - 查看集群状态
#   connect - 用obclient连接到OceanBase
#   logs    - 查看OB日志最后100行
###############################################################################

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
CONTAINER_NAME="ob-node"
CLUSTER_NAME="obcluster"
COMPOSE_DIR="$(dirname "$0")/../"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker是否运行
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker未运行，请先启动Docker"
        exit 1
    fi
}

# 启动容器和OB集群
cmd_start() {
    log_info "启动OceanBase容器..."

    cd "$COMPOSE_DIR"

    # 启动容器
    if docker-compose up -d; then
        log_info "容器启动成功"
    else
        log_error "容器启动失败"
        exit 1
    fi

    # 等待容器就绪
    log_info "等待容器就绪..."
    sleep 5

    # 启动OB集群
    log_info "启动OceanBase集群..."
    docker exec "$CONTAINER_NAME" bash -c "
        export PATH=\$HOME/.oceanbase-all-in-one/bin:\$PATH
        obd cluster start $CLUSTER_NAME 2>&1 || true
    "

    log_info "OceanBase集群启动完成"
    cmd_status
}

# 停止容器和OB集群
cmd_stop() {
    log_info "停止OceanBase集群..."

    # 优雅停止OB集群
    docker exec "$CONTAINER_NAME" bash -c "
        export PATH=\$HOME/.oceanbase-all-in-one/bin:\$PATH
        obd cluster stop $CLUSTER_NAME 2>&1 || true
        sleep 5
    " 2>/dev/null || log_warn "OB集群停止失败或未运行"

    # 停止容器
    log_info "停止容器..."
    cd "$COMPOSE_DIR"
    docker-compose down

    log_info "OceanBase已停止"
}

# 查看集群状态
cmd_status() {
    log_info "OceanBase集群状态:"
    echo ""

    # 检查容器状态
    if docker ps | grep -q "$CONTAINER_NAME"; then
        echo "容器状态: 运行中"
    else
        echo "容器状态: 未运行"
        echo ""
        return
    fi

    echo ""
    echo "集群信息:"
    docker exec "$CONTAINER_NAME" bash -c "
        export PATH=\$HOME/.oceanbase-all-in-one/bin:\$PATH
        obd cluster display $CLUSTER_NAME 2>&1
    "

    echo ""
    echo "端口监听:"
    docker exec "$CONTAINER_NAME" bash -c "
        netstat -tlnp 2>/dev/null | grep -E '2881|2882' || ss -tlnp | grep -E '2881|2882'
    "
}

# 连接到OceanBase
cmd_connect() {
    log_info "连接到OceanBase..."

    # 检查obclient是否可用
    if ! command -v obclient &> /dev/null; then
        log_error "obclient未安装"
        log_info "安装命令: apt-get install oceanbase-client"
        exit 1
    fi

    # 连接到OceanBase
    docker exec -it "$CONTAINER_NAME" bash -c "
        export PATH=\$HOME/.oceanbase-all-in-one/bin:\$PATH
        obclient -h127.0.0.1 -P2881 -uroot@sys
    "
}

# 查看日志
cmd_logs() {
    local lines=${1:-100}

    log_info "查看OceanBase日志（最后${lines}行）:"

    # 查找observer日志文件
    docker exec "$CONTAINER_NAME" bash -c "
        export PATH=\$HOME/.oceanbase-all-in-one/bin:\$PATH

        # 尝试获取日志目录
        log_dir=\$(obd cluster display $CLUSTER_NAME 2>/dev/null | grep 'log' | grep 'home' | awk '{print \$3}')

        if [ -z \"\$log_dir\" ]; then
            log_dir=\$HOME/oceanbase-data/observer/log
        fi

        echo \"日志目录: \$log_dir\"
        echo \"\"

        # 显示日志
        if [ -f \"\$log_dir/observer.log\" ]; then
            tail -n ${lines} \$log_dir/observer.log
        elif [ -f \"\$log_dir/observer.log.wf\" ]; then
            tail -n ${lines} \$log_dir/observer.log.wf
        elif [ -d \"\$log_dir\" ]; then
            # 列出日志文件
            echo \"日志文件列表:\"
            ls -lh \$log_dir/ | grep -E '\.log$'
        else
            echo \"日志目录不存在\"
            echo \"使用docker日志:\"
            docker logs --tail ${lines} $CONTAINER_NAME 2>&1 | grep -v '^$' | tail -n ${lines}
        fi
    "
}

# 进入容器shell
cmd_shell() {
    log_info "进入OceanBase容器shell..."
    docker exec -it "$CONTAINER_NAME" bash
}

# 重启集群
cmd_restart() {
    cmd_stop
    sleep 3
    cmd_start
}

# 清理并重新部署
cmd_redeploy() {
    log_warn "这将删除现有集群并重新部署"
    read -p "确认继续? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        echo "操作已取消"
        return
    fi

    log_info "停止并删除现有集群..."
    cmd_stop

    log_info "删除数据目录（可选，保留数据跳过）"
    read -p "删除数据目录? (yes/no): " delete_data

    if [ "$delete_data" = "yes" ]; then
        log_info "删除数据目录: ~/oceanbase-data"
        rm -rf ~/oceanbase-data/*
    fi

    log_info "重新部署..."
    cmd_start
}

# 显示帮助
cmd_help() {
    echo "OceanBase 管理脚本"
    echo ""
    echo "用法: $0 <command> [options]"
    echo ""
    echo "命令:"
    echo "  start      启动容器 + 启动OB集群"
    echo "  stop       优雅停止OB集群 + 停止容器"
    echo "  restart    重启OB集群"
    echo "  status     查看集群状态"
    echo "  connect    用obclient连接到OceanBase"
    echo "  logs [n]   查看OB日志最后n行（默认100行）"
    echo "  shell      进入容器shell"
    echo "  redeploy   清理并重新部署"
    echo "  help       显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 start           # 启动OceanBase"
    echo "  $0 status          # 查看状态"
    echo "  $0 logs 50         # 查看最后50行日志"
    echo "  $0 connect         # 连接到OceanBase"
    echo ""
}

# 主函数
main() {
    check_docker

    local command=${1:-help}
    shift || true

    case "$command" in
        start)
            cmd_start
            ;;
        stop)
            cmd_stop
            ;;
        restart)
            cmd_restart
            ;;
        status)
            cmd_status
            ;;
        connect)
            cmd_connect
            ;;
        logs)
            cmd_logs "$@"
            ;;
        shell)
            cmd_shell
            ;;
        redeploy)
            cmd_redeploy
            ;;
        help|--help|-h)
            cmd_help
            ;;
        *)
            log_error "未知命令: $command"
            echo ""
            cmd_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"