#!/bin/bash

###############################################################################
# OceanBase 单节点集群自动化部署脚本
#
# 适用于 Ubuntu 22.04 ARM64 环境
# 自动下载安装 OBD（OceanBase Deployer）并部署单节点集群
###############################################################################

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为admin用户
check_user() {
    if [ "$USER" != "admin" ]; then
        log_error "此脚本必须以admin用户运行"
        exit 1
    fi
    log_info "当前用户: $USER"
}

# 检查系统资源
check_resources() {
    log_info "检查系统资源..."

    # 检查内存
    total_mem=$(free -g | awk '/^Mem:/{print $2}')
    if [ "$total_mem" -lt 12 ]; then
        log_warn "系统内存少于12GB，可能影响部署"
    else
        log_info "系统内存: ${total_mem}GB"
    fi

    # 检查CPU
    cpu_count=$(nproc)
    log_info "CPU核心数: ${cpu_count}"

    # 检查磁盘空间
    data_dir="/home/admin/oceanbase-data"
    available_gb=$(df -BG "$data_dir" | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$available_gb" -lt 50 ]; then
        log_warn "可用磁盘空间少于50GB: ${available_gb}GB"
    else
        log_info "可用磁盘空间: ${available_gb}GB"
    fi
}

# 同步时间
sync_time() {
    log_info "同步系统时间..."
    sudo ntpdate time1.aliyun.com || \
    sudo ntpdate time2.aliyun.com || \
    log_warn "时间同步失败，请确保容器时间正确"
}

# 下载并安装OBD
install_obd() {
    log_info "开始安装OceanBase Deployer (OBD)..."

    # 创建临时目录
    mkdir -p ~/tmp
    cd ~/tmp

    # 下载并执行OBD安装脚本（自动检测ARM64架构）
    log_info "下载OBD安装脚本..."
    if ! bash -c "$(curl -s https://obbusiness-private.oss-cn-shanghai.aliyuncs.com/download-center/opensource/oceanbase-all-in-one/installer.sh)"; then
        log_error "OBD安装失败，请检查网络连接"
        exit 1
    fi

    # 添加环境变量
    if [ -f ~/.oceanbase-all-in-one/bin/env.sh ]; then
        source ~/.oceanbase-all-in-one/bin/env.sh
        log_info "OBD环境变量已加载"
    else
        log_error "OBD安装脚本未找到"
        exit 1
    fi

    # 验证安装
    if command -v obd &> /dev/null; then
        obd_version=$(obd --version)
        log_info "OBD安装成功: $obd_version"
    else
        # 尝试从PATH查找
        export PATH="$HOME/.oceanbase-all-in-one/bin:$PATH"
        if command -v obd &> /dev/null; then
            log_info "OBD安装成功（路径已添加）"
        else
            log_error "OBD命令未找到"
            exit 1
        fi
    fi

    cd ~
}

# 创建部署配置文件
create_config() {
    log_info "创建OceanBase部署配置文件..."

    config_file="$HOME/ob-single.yaml"
    data_dir="$HOME/oceanbase-data"

    # 确保数据目录存在
    mkdir -p "$data_dir"/{observer,store,redo}
    mkdir -p "$data_dir/log"

    # 创建配置文件（使用单节点部署，降低资源要求）
    cat > "$config_file" <<EOF
# OceanBase 单节点集群配置
# 自动生成于 $(date)

## OceanBase集群配置
oceanbase-ce:
  servers:
    - name: observer1
      ip: 127.0.0.1
      # 2881: SQL端口, 2882: RPC端口, 8080: 管理端口
      port: 2881
      rpc_port: 2882
      # 数据目录
      home_path: $data_dir/observer
      data_dir: $data_dir/store
      redo_dir: $data_dir/redo
      zone: zone1

  global:
    # 集群配置
    cluster_name: obcluster
    cluster_id: 1

    # 资源配置（单节点部署，适当降低要求）
    memory_limit: 11G          # 内存限制，留1GB给系统
    system_memory: 1G          # 系统保留内存
    datafile_size: 20G         # 数据文件大小
    log_disk_size: 15G         # 日志磁盘大小

    # CPU配置
    cpu_count: 4               # CPU核心数

    # 非生产模式（降低资源要求）
    production_mode: false

    # 租户配置
    enable_syslog_recycle: true
    max_syslog_file_count: 100
    syslog_level: INFO

    # 网络配置
    devname: eth0
    listen_port: 2881
    rpc_port: 2882

  observer1:
    # 节点特定配置（如果需要可以覆盖全局配置）
    home_path: $data_dir/observer
    data_dir: $data_dir/store
    redo_dir: $data_dir/redo
EOF

    log_info "配置文件已创建: $config_file"
}

# 部署OceanBase集群
deploy_cluster() {
    cluster_name="obcluster"

    log_info "开始部署OceanBase集群: $cluster_name"

    # 设置PATH
    export PATH="$HOME/.oceanbase-all-in-one/bin:$PATH"

    # 检查是否已存在集群
    if obd cluster list | grep -q "$cluster_name"; then
        log_warn "集群 $cluster_name 已存在，将先删除旧集群"
        obd cluster destroy "$cluster_name" || true
        sleep 5
    fi

    # 执行部署
    log_info "正在部署集群（这可能需要几分钟）..."
    if ! obd cluster deploy "$cluster_name" -c "$HOME/ob-single.yaml"; then
        log_error "集群部署失败，查看日志:"
        obd cluster display "$cluster_name" || true
        exit 1
    fi

    log_info "集群部署完成，准备启动..."
}

# 启动集群
start_cluster() {
    cluster_name="obcluster"

    log_info "启动OceanBase集群: $cluster_name"

    # 设置PATH
    export PATH="$HOME/.oceanbase-all-in-one/bin:$PATH"

    # 启动集群
    if ! obd cluster start "$cluster_name"; then
        log_error "集群启动失败"
        log_info "查看集群状态:"
        obd cluster display "$cluster_name" || true
        exit 1
    fi

    log_info "集群启动成功"
}

# 验证部署
verify_deployment() {
    cluster_name="obcluster"

    log_info "验证集群部署..."

    # 设置PATH
    export PATH="$HOME/.oceanbase-all-in-one/bin:$PATH"

    # 显示集群状态
    log_info "集群状态:"
    obd cluster display "$cluster_name"

    # 等待节点就绪
    log_info "等待节点就绪..."
    for i in {1..60}; do
        status=$(obd cluster display "$cluster_name" | grep "Status" | awk '{print $2}' || echo "")
        if echo "$status" | grep -qi "running\|active"; then
            log_info "集群已就绪"
            break
        fi
        if [ $i -eq 60 ]; then
            log_error "集群启动超时"
            exit 1
        fi
        sleep 5
    done

    # 显示集群信息
    log_info "集群信息:"
    obd cluster list
}

# 创建MySQL模式租户
create_tenant() {
    cluster_name="obcluster"

    log_info "创建MySQL模式租户..."

    # 设置PATH
    export PATH="$HOME/.oceanbase-all-in-one/bin:$PATH"

    # TODO: 根据需要修改租户配置
    # 租户名、用户名、密码等请在实际部署后手动创建
    log_warn "租户创建需要手动执行，请使用以下命令："
    echo ""
    echo "  obd cluster tenant create $cluster_name -n mysql_tenant -c \"resource_pool_size=2\""
    echo "  obclient -h127.0.0.1 -P2881 -uroot"
    echo ""
    echo "在OceanBase内执行："
    echo "  CREATE USER 'ob_user' IDENTIFIED BY 'ob_password';"
    echo "  GRANT ALL PRIVILEGES ON *.* TO 'ob_user' WITH GRANT OPTION;"
    echo ""
}

# 主函数
main() {
    echo ""
    echo "========================================"
    echo "  OceanBase 单节点集群自动化部署"
    echo "========================================"
    echo ""

    # 检查用户
    check_user

    # 检查资源
    check_resources

    # 同步时间
    sync_time

    # 安装OBD
    install_obd

    # 创建配置
    create_config

    # 部署集群
    deploy_cluster

    # 启动集群
    start_cluster

    # 验证部署
    verify_deployment

    # 创建租户提示
    create_tenant

    echo ""
    echo "========================================"
    log_info "OceanBase 部署完成！"
    echo "========================================"
    echo ""
    echo "连接信息："
    echo "  主机: 127.0.0.1"
    echo "  SQL端口: 2881"
    echo "  RPC端口: 2882"
    echo "  默认用户: root@sys"
    echo "  默认密码: (空)"
    echo ""
    echo "常用命令："
    echo "  obd cluster list              # 查看集群列表"
    echo "  obd cluster display obcluster # 查看集群详情"
    echo "  obd cluster start obcluster   # 启动集群"
    echo "  obd cluster stop obcluster    # 停止集群"
    echo "  obclient -h127.0.0.1 -P2881 -uroot  # 连接OceanBase"
    echo ""
}

# 执行主函数
main "$@"