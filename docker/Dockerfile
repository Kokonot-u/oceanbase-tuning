# OceanBase 单节点集群 Dockerfile
# 基于Ubuntu 22.04 ARM64版本
FROM ubuntu:22.04

# 设置非交互式安装
ENV DEBIAN_FRONTEND=noninteractive

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 更新包列表并安装必要依赖
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    git \
    vim \
    net-tools \
    ntpdate \
    sudo \
    python3 \
    python3-pip \
    tzdata \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 创建admin用户（OceanBase要求非root用户运行）
RUN useradd -m -s /bin/bash admin && \
    echo "admin:admin123" | chpasswd && \
    usermod -aG sudo admin

# 设置admin用户sudo免密（可选，用于测试）
RUN echo "admin ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# 创建OceanBase数据目录
RUN mkdir -p /home/admin/oceanbase-data && \
    chown -R admin:admin /home/admin/oceanbase-data

# 创建脚本目录
RUN mkdir -p /scripts && \
    chown -R admin:admin /scripts

# 切换到admin用户
USER admin
WORKDIR /home/admin

# 复制部署脚本
COPY --chown=admin:admin scripts/*.sh /scripts/

# 暴露端口
# 2881 - OceanBase MySQL协议端口
# 2882 - OceanBase RPC端口
# 8080 - OceanBase管理端口（可选）
EXPOSE 2881 2882 8080

# 保持容器运行
CMD ["tail", "-f", "/dev/null"]