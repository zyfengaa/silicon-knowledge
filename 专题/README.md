# 专题：跨模块索引

> 这里不新增一套正文，而是把散落在多个模块里的同一类问题串成一条可执行的阅读路径。
> 每个专题只回答四件事：**问题是什么、先读什么、仓库里从哪进入、数字按什么口径读**。

---

## 四个专题

| 专题 | 一句话说明 | 建议起点 |
|------|------------|----------|
| [01 精度与数值格式](01-precision-and-number-formats.md) | 从 IEEE 754 位布局到 Tensor Core / MXU，理解格式如何同时决定精度、吞吐、显存占用和可用性。 | [06-12 精度与硬件](../06-GPU架构/notes/12-precision-hardware.md) |
| [02 HBM 与存储账本](02-hbm-and-memory-ledger.md) | 把 HBM 的物理结构、带宽、容量与训练/推理的显存预算放在同一本账上。 | [05-08 HBM 与 GDDR](../05-存储层次/notes/08-hbm-and-gddr.md) |
| [03 片间互连](03-die-to-die-interconnect.md) | 区分封装内 D2D、板内 NVLink、机内 NVSwitch 与集群网络，避免把不同层次的带宽混为一谈。 | [06-08 单机与封装内互连](../06-GPU架构/notes/08-gpu-interconnect.md) |
| [04 芯片成本与良率](04-chip-cost-and-yield.md) | 从晶圆、die、良率、封装测试到 NRE 与 TCO，建立一张能复算的成本链。 | [14-05 良率模型](../14-可靠性与成本模型/notes/05-yield-models.md) |

---

## 怎么用

1. **先读“问题”**：确认你要解决的是精度选择、显存预算、互连选型还是成本估算；不要从术语表开始。
2. **沿“阅读路径”走**：每一步都给出“读什么”和“为什么现在读”，通常 3–6 步可以形成一个闭环。
3. **用“口径卡”落数**：把关键数字、单位和来源固定下来，再回到模块正文看推导。
4. **最后看“常见误区”**：这些是最容易在方案评审和容量规划里造成数量级错误的点。

---

## 按问题快速定位

| 你手上的问题 | 建议先读 |
|--------------|----------|
| FP16 训练是否还要 loss scaling？BF16 能不能直接替换？ | [专题 01](01-precision-and-number-formats.md) + [06-12](../06-GPU架构/notes/12-precision-hardware.md) |
| 为什么换到 FP8 后速度没变，甚至更慢？ | [专题 01](01-precision-and-number-formats.md) + [11 Roofline](../11-系统分析与性能工程/notes/01-roofline-model.md) |
| 70B 模型要几张卡才装得下？ | [专题 02](02-hbm-and-memory-ledger.md) + [11-08](../11-系统分析与性能工程/notes/08-end-to-end-case.md) |
| 推理长上下文的显存为什么突然爆掉？ | [专题 02](02-hbm-and-memory-ledger.md) 的 KV cache 部分 |
| 8 卡服务器为什么需要 NVSwitch？ | [专题 03](03-die-to-die-interconnect.md) + [06-08](../06-GPU架构/notes/08-gpu-interconnect.md) |
| UCIe 和 NVLink 能不能互相替代？ | [专题 03](03-die-to-die-interconnect.md) + [13-06](../13-工艺制造与先进封装/notes/06-chiplet-ucie.md) |
| 大 die 和 chiplet 哪个更便宜？ | [专题 04](04-chip-cost-and-yield.md) + [14-06](../14-可靠性与成本模型/notes/06-die-cost.md) |
| HBM 和 CoWoS 为什么占成本这么高？ | [专题 04](04-chip-cost-and-yield.md) + [14-07](../14-可靠性与成本模型/notes/07-packaging-test-cost.md) |

---

## 三个跨专题组合

- **训练容量规划**：专题 01（精度与每参数字节）→ 专题 02（模型状态、激活值、KV cache）→ 专题 03（TP/PP 带来的跨卡通信）→ 专题 04（整机 BOM 与 TCO）。
- **推理性能分析**：专题 01（低精度是否走到原生单元）→ 专题 02（权重与 KV cache 谁占主导）→ 专题 03（scale-up 域是否够大）→ 专题 04（$/token 是否下降）。
- **芯片方案评审**：专题 04（die/封装/测试成本）→ 专题 03（D2D 带宽与封装可行性）→ 专题 02（HBM 容量与带宽是否匹配）→ 专题 01（精度是否值得为面积/功耗买单）。

---

## 口径约定

- **数字单一事实来源**：算力、带宽、容量、工艺与成本量级以 [SPECS.md](../SPECS.md) 为基线；专题页只引用，不另立一套数字。
- **芯片 / 板卡 / Pod / 整机**：四种口径不可直接相加或横比。看到“900 GB/s”先问是单链路、单芯片聚合还是整机。
- **dense / sparse**：未注明时默认 dense（稠密）；2:4 稀疏峰值通常是 dense 的 2 倍，不能与 dense 数字混排。
- **GB / GiB**：GB 为 10⁹ 字节，GiB 为 2³⁰ 字节。厂商标称常混用，引用时保留原始口径并注明。
- **成本数字**：晶圆价格、HBM 单价、封装与测试费率多为公开估算或示例假设，不构成采购、报价或验收依据。
- **时间戳**：封装、HBM、互连标准演进很快；引用路线图数字时必须写年份或世代。

---

## 链接约定

- **仓库内链接**：一律使用相对路径，指向真实存在的笔记或规格文件；不链接尚未落地的占位文件。
- **兄弟仓库链接**：`why-ai-cluster` 使用绝对 URL，格式为
  `https://github.com/zyfengaa/why-ai-cluster/blob/main/<路径>`。
- **本地并排阅读**：兄弟仓库位于本仓库上一级的 `why-ai-cluster/`。
  在 Windows 资源管理器中可打开
  `D:\AI 集群 半导体 知识库\why-ai-cluster`；
  在 Markdown 中可写相对路径 `..\why-ai-cluster\<路径>`。
- 若某个计划中的文件尚未创建，专题页会明确标注“待补”，不会生成死链。

---

## 专题维护规则

- 每个专题控制在 **80–140 行**，只做索引、路径、口径和误区，不搬运模块正文的完整推导。
- 新增数字先进入 [SPECS.md](../SPECS.md)，再在专题口径卡中引用；避免同一数字出现两个版本。
- 新增专题时同步更新本页的四个专题表，保持“一句话说明 + 建议起点”的格式。
- 模块内新增关键笔记后，回到相关专题补一条入口，而不是在专题里复制内容。

---

## 文件清单

- [01-precision-and-number-formats.md](01-precision-and-number-formats.md)
- [02-hbm-and-memory-ledger.md](02-hbm-and-memory-ledger.md)
- [03-die-to-die-interconnect.md](03-die-to-die-interconnect.md)
- [04-chip-cost-and-yield.md](04-chip-cost-and-yield.md)
