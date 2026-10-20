# 专题 03：片间互连

> “片间互连”至少跨越四个层次：封装内 die-to-die（D2D）、板内/机内 GPU 互连、机架内交换、集群网络。
> 本专题先把层次分开，再比较带宽、延迟、距离与成本；不要把不同层次的 GB/s 直接相加。

---

## 问题

- PCIe、NVLink、NVSwitch、UCIe 分别解决“哪一段距离”的连接？哪些是协议，哪些是封装技术？
- 为什么 PCIe 5.0 x16 有的表写 64 GB/s，有的表写 50 GB/s？差别在原始线路速率还是有效载荷？
- NVLink 4 的 900 GB/s、NVLink 5 的 1.8 TB/s 是单向还是双向？是单链路还是整颗 GPU 聚合？
- NVSwitch 为什么出现？8 卡全互联和 72 卡 NVLink 域分别需要什么拓扑？
- B200 两个计算 die 之间的 NV-HBI 与 GPU 之间的 NVLink 是不是同一种东西？
- UCIe 的 32 GT/s、凸点间距和带宽密度如何换算？为什么“带宽密度”的单位是 GB/s/mm 而不是 GB/s？
- 什么时候该用 scale-up（纵向扩展），什么时候必须走 scale-out（横向扩展）？

---

## 阅读路径

1. **先建立层次感。** 读 [06-08 单机与封装内互连](../06-GPU架构/notes/08-gpu-interconnect.md)。先看 PCIe 的 CPU-GPU 路径，再看 NVLink 的 GPU-GPU 点对点连接，最后看 NVSwitch 如何把 8 卡/72 卡做成一个高带宽域。
2. **进入封装内部。** 读 [13-06 Chiplet 与 UCIe](../13-工艺制造与先进封装/notes/06-chiplet-ucie.md)，理解 D2D 接口为什么采用并行、短距、源同步（source-synchronous）结构，以及 UCIe 的协议层/适配层/物理层。
3. **看封装如何承载互连。** 读 [13-07 2.5D/3D 先进封装](../13-工艺制造与先进封装/notes/07-advanced-packaging.md)，重点看硅中介层、EMIB、CoWoS、凸点间距（bump pitch）和“芯片边缘带宽”（beachfront）的约束。
4. **补一个非 NVIDIA 的 scale-up 参照。** 读 [09-08 TPU Pod](../09-Google-TPU/notes/08-tpu-pod.md)，观察 TPU 的 ICI、2D/3D Torus 与 OCS 如何组织 Pod；它与 NVLink 域是不同路线，但面对的是同一类拓扑问题。
5. **用 SPECS §5.2/§5.3 校准。** 回到 [SPECS.md](../SPECS.md)，统一 PCIe/NVLink/NVSwitch/ICI 的单向、双向、每链路、每设备口径。
6. **最后进入集群层。** 读兄弟仓库的 PCIe/NVLink、NVSwitch 和网络拓扑三篇，把“域内”与“域间”接起来。

---

## 仓库入口

| 入口 | 读什么 | 在本路径中的位置 |
|------|--------|------------------|
| [06-08 单机与封装内互连](../06-GPU架构/notes/08-gpu-interconnect.md) | PCIe 代际、P2P、NVLink 演进、NVSwitch、NVLink 域 | 本专题主干 |
| [13-06 Chiplet 与 UCIe](../13-工艺制造与先进封装/notes/06-chiplet-ucie.md) | 拆 die 的理由、UCIe 分层、D2D 指标、UCIe/BoW/NV-HBI/EMIB 对比 | 封装内 D2D |
| [13-07 2.5D/3D 先进封装](../13-工艺制造与先进封装/notes/07-advanced-packaging.md) | CoWoS-S/R/L、EMIB、混合键合、凸点间距、HBM 集成 | D2D 的物理承载 |
| [09-08 TPU Pod](../09-Google-TPU/notes/08-tpu-pod.md) | ICI、Torus、OCS、Pod 级 All-Reduce | 非 NVIDIA 的 scale-up 参照 |
| [SPECS.md](../SPECS.md) | §5.2 互连表、§5.3 NVSwitch 与 NVLink 域 | 数字校准 |

---

## 兄弟仓库入口

| 文档 | 解决的问题 | 本地并排路径 |
|------|------------|--------------|
| [02 PCIe 瓶颈与 NVLink 诞生](https://github.com/zyfengaa/why-ai-cluster/blob/main/02-芯片篇/02-PCIe瓶颈与NVLink诞生.md) | 为什么 PCIe 成为 GPU-GPU 瓶颈，NVLink 如何绕过 CPU/Root Complex | `..\why-ai-cluster\02-芯片篇\02-PCIe瓶颈与NVLink诞生.md` |
| [03 NVSwitch 为什么出现](https://github.com/zyfengaa/why-ai-cluster/blob/main/02-芯片篇/03-NVSwitch为什么出现.md) | 8 卡全互联的链路账，NVSwitch 如何扩展 NVLink 域 | `..\why-ai-cluster\02-芯片篇\03-NVSwitch为什么出现.md` |
| [05 网络拓扑怎么选](https://github.com/zyfengaa/why-ai-cluster/blob/main/03-网络篇/05-网络拓扑怎么选.md) | Fat-Tree、Rail-optimized、Dragonfly+、3D Torus 的选型 | `..\why-ai-cluster\03-网络篇\05-网络拓扑怎么选.md` |

> 兄弟仓库 `why-ai-cluster` 与本仓库并排放在 `D:\AI 集群 半导体 知识库\` 下。
> 上面的绝对 URL 分别对应本地 `..\why-ai-cluster\02-芯片篇\...` 与
> `..\why-ai-cluster\03-网络篇\05-网络拓扑怎么选.md`。

---

## 口径卡

| 项目 | 数字 / 口径 | 来源与提醒 |
|------|-------------|------------|
| PCIe 5.0 x16 | SPECS 有效载荷近似：单向约 50 GB/s，双向约 100 GB/s | SPECS §5.2；128b/130b 编码与协议开销已折算 |
| PCIe 5.0 x16（原始线路） | 约 64 GB/s 单向，约 128 GB/s 双向 | 06-08 表；这是线路速率折算口径，与 SPECS 的有效载荷口径不同 |
| PCIe 6.0 x16 | 单向约 100 GB/s，双向约 200 GB/s | SPECS §5.2；PAM4 + FLIT + FEC，不能套用 128b/130b 算法 |
| NVLink 4 | 每链路 25 GB/s 单向、50 GB/s 双向；18 链路合计 900 GB/s 双向 | SPECS §5.2；900 GB/s 是整颗 GPU 的双向聚合，不是单向 |
| NVLink 5 | 每链路 50 GB/s 单向、100 GB/s 双向；18 链路合计 1.8 TB/s 双向 | SPECS §5.2；B200 的 GPU 间互连 |
| NVSwitch 3 | 64 端口，单端口 50 GB/s 双向，聚合约 3.2 TB/s | SPECS §5.3；DGX H100 用 4 颗，域上限 8 GPU |
| NVSwitch 4 | 72 端口，单端口 100 GB/s 双向，聚合约 7.2 TB/s | SPECS §5.3；NVL72 用 18 颗，域上限 72 GPU |
| NVLink 域 | H100 8 卡；NVL72 72 卡；Rubin NVL144、Rubin Ultra NVL576 为路线图 | SPECS §5.3；域内 NVLink，域间 IB/以太网 |
| NVLink-C2C | Grace Hopper 约 900 GB/s 双向 | SPECS §5.2；CPU-GPU 一致性互连，不是 GPU-GPU NVLink |
| NV-HBI | B200 双计算 die 之间约 10 TB/s | SPECS §7.3；私有 D2D，把双 die 组成一个逻辑 GPU |
| UCIe 1.0 | 4–32 GT/s；标准封装凸点 100–130 µm，先进封装 25–55 µm | SPECS §7.3；带宽密度分别约 28–224 与 165–1317 GB/s/mm |
| UCIe 3.0 | 每 lane 48/64 GT/s | 13-06；2025 规范，引用时必须写版本 |
| CoWoS 尺寸 | CoWoS-S 约 3.3× reticle（约 2,700 mm²）；CoWoS-L 3.5× 量产、5.5× 开发中 | SPECS §7.3；路线图口径，引用时写年份 |
| TPU ICI | v4 约 600 GB/s/芯片；v5p 约 1,200 GB/s/芯片 | SPECS §5.2；与 NVLink 域不是同一协议 |
| 带宽单位 | 区分单向/双向、每链路/每设备、原始线路/有效载荷 | 本专题最重要的口径纪律 |

---

## 常见误区

1. **“NVLink 4 是 900 GB/s 单向。”**
   900 GB/s 是 18 条链路、每条 50 GB/s 双向的聚合双向带宽；单向聚合是 450 GB/s。厂商标称和论文常默认“双向合计”，引用时必须写清楚。

2. **“NVSwitch 让整个集群变成全互联。”**
   NVSwitch 扩展的是 NVLink 域：H100 为 8 卡，NVL72 为 72 卡。域间仍要走 InfiniBand 或以太网；DGX SuperPOD 的 256 卡不是 256 卡 NVLink 全互联。

3. **“PCIe 5.0 x16 就是 128 GB/s 单向。”**
   128 GB/s 是双向原始线路口径；有效载荷还要扣除编码和协议开销。SPECS 采用约 50 GB/s 单向、100 GB/s 双向的近似，06-08 采用约 64/128 GB/s 的线路口径，两者不是同一个数。

4. **“UCIe 是一种封装技术，或者可以替代 NVLink。”**
   UCIe 是 die-to-die 的协议/适配层/PHY 标准，跑在中介层、桥接或有机基板上；EMIB、CoWoS 才是封装实现。UCIe 解决封装内短距互连，不替代机内 NVLink 或集群网络。

5. **“NV-HBI 就是 B200 的 NVLink。”**
   NV-HBI 是 B200 两个计算 die 之间的私有 D2D 接口，约 10 TB/s；NVLink 5 是 GPU 之间的互连。两者层次不同，不能拿 10 TB/s 与 1.8 TB/s 直接比较。

6. **“链路数越多，互连一定越好。”**
   链路数受芯片边缘（beachfront）、凸点间距、功耗、封装层数和成本约束；协议开销、拓扑收敛比和软件路径也会决定实际带宽。D2D 带宽密度常以 GB/s/mm 计，不是单纯堆 lane 数。

7. **“TPU 的 ICI 就是以太网。”**
   TPU v4/v5p 的 ICI 是专用的芯片间互连，配合 Torus/OCS 组织 Pod；它与 InfiniBand/RoCE 的协议、拓扑和运维方式都不同。

---

## 读完后应能回答

- 给定通信距离和带宽需求，判断应该用 UCIe、NVLink、NVSwitch 还是 InfiniBand/以太网。
- 把厂商标称的“每链路、每设备、单向、双向”换算成同一口径。
- 解释为什么 8 卡全互联需要 NVSwitch，以及为什么 72 卡域仍然不是“整个集群”。
