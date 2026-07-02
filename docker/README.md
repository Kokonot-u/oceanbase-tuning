# OceanBase Docker 部署

在macOS（Apple M4）上使用Docker部署OceanBase单节点集群。

## 系统要求

- macOS with Apple Silicon (ARM64)
- Docker Desktop 或 OrbStack
- 至少 16GB 内存（推荐 24GB+）
- 至少 50GB 可用磁盘空间

## 部署步骤

### 1. 启动容器

```bash
cd docker
docker-compose up -d
```

### 2. 进入容器

```bash
docker exec -it ob-node bash
```

### 3. 在容器内部署OceanBase

```bash
bash /scripts/install_ob.sh
```

部署过程大约需要 5-10 分钟，包括：
- 下载并安装OBD
- 配置OceanBase集群
- 启动Observer进程

### 4. 退出容器并验证

```bash
exit
python docker/scripts/verify_connection.py
```

### 5. 更新项目配置

验证通过后，将连接信息填入 `config/db_config.yaml`：

```yaml
host: "127.0.0.1"
port: 2881
user: "root@sys"
password: ""
database: "oceanbase"
charset: utf8mb4
```

## 快捷操作脚本

使用 `ob_manager.sh` 快速管理OceanBase集群：

```bash
chmod +x docker/scripts/ob_manager.sh

# 启动
./docker/scripts/ob_manager.sh start

# 停止
./docker/scripts/ob_manager.sh stop

# 查看状态
./docker/scripts/ob_manager.sh status

# 连接数据库
./docker/scripts/ob_manager.sh connect

# 查看日志
./docker/scripts/ob_manager.sh logs

# 进入容器shell
./docker/scripts/ob_manager.sh shell
```

## 连接信息

| 项目 | 值 |
|------|-----|
| 主机 | 127.0.0.1 |
| SQL端口 | 2881 |
| RPC端口 | 2882 |
| 默认用户 | root@sys |
| 默认密码 | （空） |

## 常见问题

### 1. 部署失败：内存不足

如果遇到内存不足错误，尝试：
- 增加 Docker 内存限制（Docker Desktop -> Settings -> Resources）
- 修改 `docker-compose.yml` 中的 `memory_limit`

### 2. 节点状态不为ACTIVE

检查容器时间是否同步：
```bash
docker exec ob-node date
```

确保与宿主机时间一致。

### 3. 端口冲突

如果2881或2882端口被占用，修改 `docker-compose.yml` 中的端口映射。

### 4. 重新部署

```bash
./docker/scripts/ob_manager.sh stop
rm -rf ~/oceanbase-data/*
./docker/scripts/ob_manager.sh start
# 然后重新执行 install_ob.sh
```

### 5. 查看详细日志

```bash
docker exec -it ob-node bash
obd cluster display obcluster
tail -f ~/oceanbase-data/observer/log/observer.log
```

## 配置说明

### 资源配置

| 配置项 | 值 | 说明 |
|--------|-----|------|
| CPU | 4核 | Docker限制 |
| 内存 | 12GB | Docker限制 |
| memory_limit | 11GB | Observer内存限制 |
| system_memory | 1GB | 系统保留内存 |
| datafile_size | 20GB | 数据文件大小 |
| log_disk_size | 15GB | 日志磁盘大小 |

### 单节点部署特点

- `production_mode: false` - 非生产模式，降低资源要求
- 单zone部署（zone1）
- 单observer节点

## 后续操作

### 创建租户

```sql
-- 连接到OceanBase后执行
CREATE RESOURCE POOL pool1 UNIT_COUNT = 1, UNIT_CONFIG = 'memory_size=4G,max_cpu=2';
CREATE TENANT mysql_tenant CHARACTER SET utf8mb4 SET 'utf8mb4_general_ci',
    RESOURCE_POOL_LIST=('pool1'), SET ob_tcp_invited_nodes='%';
```

### 创建用户

```sql
CREATE USER 'ob_user'@'%' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON *.* TO 'ob_user'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;
```

## 注意事项

1. **ARM架构兼容性**: 所有组件已配置为ARM64/aarch64版本
2. **时间同步**: 容器时间必须正确，否则集群无法启动
3. **资源限制**: 单节点部署最低需要12GB内存
4. **生产部署**: 此配置仅用于开发测试，生产环境请使用集群部署
5. **数据持久化**: 数据存储在 `~/oceanbase-data` 目录

## 参考资料

- [OceanBase 官方文档](https://www.oceanbase.com/docs)
- [OBD 使用指南](https://www.oceanbase.com/docs/community-observer-cn-10000000000903417)