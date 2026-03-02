# 故障注入工具集

本文档汇总了各类故障注入工具，按故障类别分类。

## 网络故障注入工具

### 1. tc + netem (Network Emulator)
**适用**: Linux 网络

```bash
# 延迟
tc qdisc add dev eth0 root netem delay 100ms

# 丢包
tc qdisc add dev eth0 root netem loss 2%

# 抖动
tc qdisc add dev eth0 root netem delay 100ms 50ms

# 重复包
tc qdisc add dev eth0 root netem duplicate 1%

# 损坏包
tc qdisc add dev eth0 root netem corrupt 0.1%

# 乱序
tc qdisc add dev eth0 root netem delay 100ms reorder 0.5%

# 组合
tc qdisc add dev eth0 root netem delay 100ms loss 1% duplicate 1%
```

**清理**:
```bash
tc qdisc del dev eth0 root
```

### 2. iptables
**适用**: 防火墙规则

```bash
# 丢弃所有包
iptables -A INPUT -j DROP

# 丢弃特定端口
iptables -A INPUT -p tcp --dport 8080 -j DROP

# 丢弃特定 IP
iptables -A INPUT -s 192.168.1.100 -j DROP

# 拒绝连接（RST）
iptables -A INPUT -p tcp --dport 8080 -j REJECT

# 限速
iptables -A INPUT -m limit --limit 10/second -j ACCEPT
iptables -A INPUT -j DROP

# 随机丢包
iptables -A INPUT -m statistic --mode random --probability 0.01 -j DROP
```

### 3. chaos-mesh
**适用**: Kubernetes

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: network-delay
spec:
  action: delay  # delay, loss, duplicate, corrupt
  mode: all
  selector:
    namespaces:
      - default
    labelSelectors:
      app: myapp
  delay:
    latency: "100ms"
    correlation: "25"
    jitter: "50ms"
  direction: to  # to, from, both
```

### 4. Toxiproxy
**适用**: 代理层故障注入

```bash
# 创建代理
toxiproxy-cli create mysql -h localhost -p 3306 -t localhost:3307

# 添加延迟
toxiproxy-cli toxic add mysql -t latency -a latency=1000

# 添加丢包
toxiproxy-cli toxic add mysql -t slow_close

# 添加超时
toxiproxy-cli toxic add mysql -t timeout -a timeout=100
```

## 存储故障注入工具

### 1. scsi_debug
**适用**: SCSI 设备故障

```bash
# 加载模块
modprobe scsi_debug

# 模拟介质错误
echo 1 > /sys/bus/pseudo/drivers/scsi_debug/medium_error_count

# 模拟超时
echo 300 > /sys/bus/pseudo/drivers/scsi_debug/timeout

# 查看设备
lsscsi
```

### 2. dmsetup (Device Mapper)
**适用**: 块设备故障

```bash
# 延迟设备
modprobe dm-delay
dmsetup create delayed-disk --table \
  "0 $(blockdev --getsize /dev/sdb) delay /dev/sdb 0 100"

# 故障设备
modprobe dm-flakey
dmsetup create flakey-disk --table \
  "0 $(blockdev --getsize /dev/sdb) flakey /dev/sdb 0 10"

# 错误设备
modprobe dm-error
dmsetup create error-disk --table \
  "0 $(blockdev --getsize /dev/sdb) error /dev/sdb"
```

### 3. fault-injection-toolkit
**适用**: 文件系统故障

```bash
# 模拟磁盘满
dd if=/dev/zero of=/disk/file.img bs=1G count=100

# 模拟只读
mount -o remount,ro /disk

# 模拟 I/O 错误
debugfs -w /dev/sdb1
debugfs: clri <inode_number>
```

### 4. failfs
**适用**: FUSE 故障注入

```bash
git clone https://github.com/richo/failfs
cd failfs

# 创建故障文件系统
./failfs /mnt/failfs /data

# 注入故障
echo "eio" > /mnt/failfs/control  # I/O 错误
echo "enospc" > /mnt/failfs/control  # 空间不足
echo "enomem" > /mnt/failfs/control  # 内存不足
```

## 计算资源故障注入工具

### 1. stress-ng
**适用**: CPU/内存/IO 压力

```bash
# CPU 压力
stress-ng --cpu 4 --cpu-method all --timeout 60s

# 内存压力
stress-ng --vm 2 --vm-bytes 1G --timeout 60s

# I/O 压力
stress-ng --io 4 --iomix --timeout 60s

# 组合
stress-ng --cpu 2 --vm 1 --io 1 --timeout 60s
```

### 2. cpulimit
**适用**: CPU 限制

```bash
# 限制进程 CPU 使用
cpulimit -l 50 -p 1234  # 限制为 50%

# 限制命令
cpulimit -l 20 -- your-command
```

### 3. cgroups
**适用**: 资源隔离

```bash
# 创建 cgroup
mkdir /sys/fs/cgroup/cpu/test
echo 51200 > /sys/fs/cgroup/cpu/test/cpu.cfs_quota_us  # 50%
echo 100000 > /sys/fs/cgroup/cpu/test/cpu.cfs_period_us

# 限制进程
echo $PID > /sys/fs/cgroup/cpu/test/cgroup.procs
```

### 4. taskset
**适用**: CPU 亲和性

```bash
# 绑定到特定 CPU
taskset -c 0 your-command  # 只使用 CPU 0

# 排除特定 CPU
taskset -c 0-2 your-command  # 使用 CPU 0,1,2
```

## 内存故障注入工具

### 1. memtester
**适用**: 内存测试

```bash
# 测试 1GB 内存，循环 10 次
memtester 1G 10

# 测试特定进程内存
memtester --pid $PID 100M 5
```

### 2. failmalloc
**适用**: 内存分配失败模拟

```bash
# 编译
git clone https://github.com/nicupavel/failmalloc
cd failmalloc && make

# 使用
LD_PRELOAD=./libfailmalloc.so FAILPROB=0.1 your-program
```

### 3. mce-test
**适用**: Machine Check Exception

```bash
git clone https://git.kernel.org/pub/scm/linux/kernel/git/gong/mce-test.git
cd mce-test

# 运行测试
./runtests.sh
```

## 进程故障注入工具

### 1. kill 信号
```bash
# SIGTERM (15) - 正常终止
kill -15 $PID

# SIGKILL (9) - 强制杀死
kill -9 $PID

# SIGSTOP (19) - 暂停进程
kill -19 $PID

# SIGCONT (18) - 恢复进程
kill -18 $PID

# SIGSEGV (11) - 段错误
kill -11 $PID
```

### 2. pkill
```bash
# 按名称杀进程
pkill -9 nginx

# 按模式杀进程
pkill -9 -f "python.*script"
```

### 3. chaos-mesh Pod Failure
```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: pod-kill
spec:
  action: pod-kill  # pod-failure, container-kill
  mode: one
  selector:
    namespaces:
      - default
    labelSelectors:
      app: myapp
```

### 4. crashes
```python
# Python 崩溃注入
import os
import signal

# Segfault
import ctypes
ctypes.string_at(0)

# Abort
os.abort()

# Kill self
os.kill(os.getpid(), signal.SIGKILL)
```

## 系统调用故障注入工具

### 1. failmalloc
**适用**: malloc 失败

```bash
LD_PRELOAD=/path/to/libfailmalloc.so FAILPROB=0.1 ./program
```

### 2. libfiu (Fault Injection Userspace)
```bash
git clone https://github.com/alban/fiu
cd fiu && make

# 注入故障
fiu-run -x -c -i -1 'enable/name=posix/io/io,*' ./program
```

### 3. eBPF 故障注入
```python
#!/usr/bin/env bpftrace
# 跟踪并注入失败

kprobe:tcp_v4_connect
/comm == "nginx"/
{
    // 返回错误
    @errored[comm] = count();
}
```

## 时间故障注入工具

### 1. libfaketime
```bash
# 安装
git clone https://github.com/wolfcw/libfaketime
cd libfaketime && make

# 使用
LD_PRELOAD=./libfaketime.so.1 FAKETIME="+10d" ./program
FAKETIME="2024-01-01 00:00:00" ./program
FAKETIME_RATE=2 ./program  # 时间加速 2 倍
```

### 2. date 修改 (危险!)
```bash
# 修改系统时间
date -s "2024-01-01 00:00:00"

# 恢复
ntpdate pool.ntp.org
```

### 3. adjtimex
```bash
# 调整时间偏移
adjtimex -f 1000000  # 1 秒偏移

# 恢复
adjtimex -f 0
```

## 硬件故障注入工具

### 1. IPMI
```bash
# 模拟电源故障
ipmitool power cycle

# 模拟温度过高
ipmitool sensor thresh ...  # 需要 BMC 支持

# 模拟风扇故障
ipmitool raw ...  # 厂商特定命令
```

### 2. QEMU/KVM
```bash
# 模拟磁盘故障
qemu-system-x86_64 -drive file=disk.qcow2,if=virtio,discard=unmap \
  -drive file=corrupt.img,if=virtio

# 模拟网络故障
qemu-system-x86_64 -net nic,model=virtio -net user,restrict=y

# 注入 NMI
qemu-system-x86_64 -nographic -monitor pty
# 在 monitor: nmi xxx
```

## 综合故障注入平台

### 1. Chaos Mesh (Kubernetes)
```bash
# 安装
curl -sSL https://mirrors.chaos-mesh.org/latest/install.sh | bash

# 网络故障
kubectl apply -f network-chaos.yaml

# Pod 故障
kubectl apply -f pod-chaos.yaml

# IO 故障
kubectl apply -f io-chaos.yaml

# Kernel 故障
kubectl apply -f kernel-chaos.yaml
```

### 2. LitmusChaos
```bash
# 安装
kubectl apply -f https://litmuschaos.github.io/litmus/litmus-operator-v2.11.0.yaml

# 运行 Chaos 实验
litmusctl experiment run \
  --name nginx-pod-delete \
  --namespace default
```

### 3. Gremlin
```bash
# 安装 Agent
curl -O https://dev.gremlin.com/clients/gremlin/gremlin-init.sh
bash gremlin-init.sh YOUR_API_KEY

# 运行实验
gremlin attack cpu --percent 50 --duration 60
gremlin attack memory --percent 50 --duration 60
gremlin attack network --interface eth0 --delay 100 --percent 0.01
```

### 4. Chaos Monkey (Spinnaker)
```json
{
  "description": "Terminate random instances",
  "rules": [
    {
      "action": "terminate",
      "probability": 0.5
    }
  ]
}
```

## 自定义故障注入脚本

### 完整的故障注入框架

```python
#!/usr/bin/env python3
"""
通用故障注入框架
"""

import subprocess
import time
import argparse

class FaultInjector:
    """故障注入器基类"""

    def __init__(self, target):
        self.target = target
        self.backup = None

    def inject(self):
        """注入故障"""
        raise NotImplementedError

    def recover(self):
        """恢复故障"""
        raise NotImplementedError

class NetworkFaultInjector(FaultInjector):
    """网络故障注入"""

    def inject(self, delay=None, loss=None):
        cmd = ["tc", "qdisc", "add", "dev", self.target, "root", "netem"]

        if delay:
            cmd.extend(["delay", f"{delay}ms"])
        if loss:
            cmd.extend(["loss", f"{loss}%"])

        subprocess.run(cmd, check=True)

    def recover(self):
        subprocess.run(["tc", "qdisc", "del", "dev", self.target, "root"],
                      check=False)

class ProcessFaultInjector(FaultInjector):
    """进程故障注入"""

    def inject(self, signal=9):
        subprocess.run(["kill", f"-{signal}", self.target], check=True)

    def recover(self):
        pass  # 进程无法恢复

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", choices=["network", "process"])
    parser.add_argument("--target")
    parser.add_argument("--delay", type=int)
    parser.add_argument("--loss", type=float)
    args = parser.parse_args()

    if args.type == "network":
        injector = NetworkFaultInjector(args.target)
        injector.inject(delay=args.delay, loss=args.loss)
        print(f"Injected network fault, waiting 60s...")
        time.sleep(60)
        injector.recover()
```

## 使用建议

1. **渐进式测试**: 从轻微故障开始，逐渐增加强度
2. **自动化**: 将故障注入集成到 CI/CD
3. **可观测**: 确保有足够的监控和日志
4. **可恢复**: 始终有回滚方案
5. **安全性**: 避免在生产环境直接测试

## 参考资料

- [Chaos Engineering Principles](https://principlesofchaos.org/)
- [Chaos Mesh Documentation](https://chaos-mesh.org/docs/)
- [LitmusChaos Documentation](https://litmuschaos.io/docs/)
- [Linux tc-netem](https://man7.org/linux/man-pages/man8/tc-netem.8.html)
