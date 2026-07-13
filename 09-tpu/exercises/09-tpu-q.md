# 模块 09 — TPU 练习题

---

## 问题 1：TPU 世代对比表（TPU Generation Comparison Table）

创建 TPU 世代 v1、v2、v3、v4 和 v5p 的详细对比表。填写每个世代的以下维度。如果某个具体值未公开，请标记为"N/A"并根据现有文献提供估计值或范围。

| 维度 | v1 | v2 | v3 | v4 | v5p |
|-----------|----|----|----|----|-----|
| MAC 数量 | | | | | |
| 片上内存 | | | | | |
| DRAM/HBM 容量 | | | | | |
| DRAM/HBM 带宽 | | | | | |
| INT8 TOPS | | | | | |
| BF16 TFLOPS | | | | | |
| Die TDP | | | | | |
| 芯片间互联 | | | | | |

**填写表格后回答问题：**
1. 哪个世代相比其前代有最大的相对性能提升？
2. 各世代之间互联设计的趋势是什么？
3. 为什么 Google 从 DDR（v1）切换到 HBM（v2+）？

---

## 问题 2：MXU 与 Tensor Core 对比（MXU vs Tensor Core）

比较 Google 的 MXU（Matrix Multiply Unit，用于 TPU）和 NVIDIA 的 Tensor Core。

**2a)** 描述两种架构在实现上的根本区别：
- 每种架构如何计算矩阵乘法？
- 精度支持有何不同？
- 从软件角度看它们的可编程性如何？

**2b)** 画一个简单的状态图（文本/ASCII art 或流程图表示），展示 2x2 MXU 脉动阵列（systolic array）如何计算：
```
C = A x B
```
其中：
- A = [[a11, a12],
        [a21, a22]]
- B = [[b11, b12],
        [b21, b22]]

追踪多周期数据流通过阵列的过程，展示每个周期中每个处理单元（PE）中的值。

**2c)** 在什么场景下 MXU 的脉动阵列方法优于 Tensor Core，反之亦然？

---

## 问题 3：OCS 的优势（OCS Advantages）

解释光路交换机（Optical Circuit Switches, OCS）如何在 TPU v4 中实现可重配置拓扑（reconfigurable topology）。

**3a)** 描述 OCS 的物理机制（MEMS 反射镜阵列）以及信号是如何路由的。

**3b)** 列出并解释光交换相对于固定电互联（如 TPU v2/v3 的 2D Torus 或 NVIDIA 的 NVLink）的至少 4 个优势：

1. 多租户隔离（Multi-tenant isolation）
2. 容错性（Fault tolerance）
3. 资源分配灵活性（Resource allocation flexibility）
4. 能效（Power efficiency）

**3c)** OCS 如何影响大型数据中心中的训练任务调度？考虑：
- 碎片避免（Fragmentation avoidance）
- 任务打包效率（Job packing efficiency）
- 混合工作负载支持（小任务 vs 大任务）

**3d)** OCS 的局限性有哪些？什么时候仍然更倾向于使用固定电互联？

---

## 问题 4：TPU 与 GPU 的权衡（TPU vs GPU Tradeoffs）

对于以下每种工作负载场景，判断 TPU 或 GPU 哪个更合适，并用 2-3 句话解释理由。

| 场景 | 更好的选择？ | 理由 |
|----------|---------------|-----------|
| 在 1024 个芯片上大批量训练稠密 Transformer（100B 参数） | | |
| BERT-Large 的低延迟推理（batch size=1） | | |
| 训练具有 100B 嵌入表的推荐模型 | | |
| 小批量训练 1B 参数 CNN 以快速原型验证 | | |
| 总参数为 1T 的稀疏混合专家（MoE）模型 | | |
| 功耗小于 50W 的边缘设备推理 | | |
| 科学计算（FP64 矩阵运算） | | |
| 训练结合视觉、文本和音频的多模态模型 | | |

---

## 问题 5：XLA 编译器优化（XLA Compiler Optimization）

追踪从高层模型（TensorFlow 或 JAX）到 TPU 可执行文件的编译路径。每个阶段对计算图进行不同的变换。

**5a)** 对于以下每个编译阶段，描述其输入、输出以及执行的关键变换：

| 阶段 | 输入 | 输出 | 关键变换 |
|-------|-------|--------|-------------------|
| HLO 构建 | | | |
| HLO 优化 | | | |
| 并行化（SPMD Partitioner） | | | |
| 代码生成 | | | |

**5b)** 算子融合示例（Operator Fusion Example）：

考虑以下计算：
```
h = jnp.concatenate([x, y])
z = jnp.dot(W, h)
out = jnp.sum(z, axis=1)
```

不进行融合时，XLA 会产生多少次 kernel 启动？进行融合后，XLA 会产生多少次 kernel 启动？逐步追踪融合过程。

**5c)** 为什么算子融合对 TPU 性能尤其重要（比 GPU 更重要）？提示：思考存储层次结构以及 Unified Buffer / HBM 的作用。

---

## 参考答案（Answer Key）

### 答案 1：TPU 世代对比表

| 维度 | v1 | v2 | v3 | v4 | v5p |
|-----------|----|----|----|----|-----|
| MAC 数量 | 65,536 (INT8) | 32,768 (BF16 每个 MXU, 2 个 MXU) | 65,536 (BF16 每个 MXU, 4 个 MXU) | ~131K (BF16, 每核心 4 个 MXU, 2 核心) | ~262K (估计) |
| 片上内存 | 28 MB UB + 4 MB FIFO | ~12 MB (寄存器+缓存) | ~30 MB (估计) | ~44 MB (估计) | ~60 MB (估计) |
| DRAM/HBM 容量 | 8 GB DDR3 | 16 GB HBM | 32 GB HBM | 32 GB HBM | 95 GB HBM |
| DRAM/HBM 带宽 | ~34 GB/s (DDR3) | ~600 GB/s | ~900 GB/s | ~1200 GB/s | ~1600 GB/s (估计) |
| INT8 TOPS | 92 TOPS | N/A (主要为 BF16) | N/A | ~275 TOPS | ~500 TOPS (估计) |
| BF16 TFLOPS | N/A | 45 TFLOPS | 123 TFLOPS | 275 TFLOPS | 459 TFLOPS |
| Die TDP | 75 W | 280 W | 450 W | ~400 W (估计) | ~400 W (估计) |
| 芯片间互联 | PCIe Gen3 x16 | 2D Torus (定制) | 2D Torus (定制) | OCS (光) + 2D Torus | OCS + 2D Torus |

**后续问题答案：**

1. TPU v3 相比 v2 具有最大的相对性能提升（每芯片 BF16 TFLOPS 约提升 2.7 倍）。从 v1 到 v2 的转变也代表了巨大的架构变化（从推理到训练）。

2. 互联趋势：从 PCIe（独立）到定制 2D Torus（紧耦合）再到 OCS + Torus（可重配置）。每一代都向更可扩展、更灵活的网络方向发展。

3. DDR3 足以用于推理，但缺乏训练所需的带宽。训练在正向/反向传播过程中需要频繁读写激活值和梯度，这使得 HBM 的高带宽成为必需。

---

### 答案 2：MXU 与 Tensor Core 对比

**2a) 根本区别：**

- **实现方式**：MXU 是纯脉动阵列（systolic array）——数据以有节奏的波形式流过处理单元，最小化寄存器文件访问。Tensor Core 是一种 warp 级矩阵乘加单元，对加载到寄存器中的矩阵分片（fragments）进行操作。

- **精度**：MXU 原生支持 BF16 输入和 FP32 累加。Tensor Core 支持 FP16、BF16、TF32、INT8、INT4 和 FP64（取决于 GPU 世代）。

- **可编程性**：MXU 完全由 XLA 编译器控制——程序员无法直接访问。Tensor Core 可通过 cuBLAS、cuDNN、CUDA C++（wmma API）和 Triton 访问，提供更多灵活性。

**2b) 2x2 MXU 脉动阵列状态图（C = A x B）：**

```
权重（B）预先加载：
  PE[0,0] 存储 b11    PE[0,1] 存储 b12
  PE[1,0] 存储 b21    PE[1,1] 存储 b22

周期 1：
  输入 a11 从左侧进入。
  PE[0,0]：temp = a11 * b11，部分和 = temp，向右传递到 PE[0,1]
  PE[0,1]：接收 temp，临时存储
  PE[1,0], PE[1,1] 空闲

周期 2：
  输入 a12 从左侧进入。
  PE[0,0]：temp = a12 * b11，部分和 = temp，向右传递到 PE[0,1]
  PE[0,1]：temp2 = a11 * b12，和 = temp + temp2，向下传递到 PE[1,1]
  输入 a21 从左上进入。
  PE[0,0] 也将 a21 向下传递到 PE[1,0]

周期 3：
  PE[0,0]：（无新输入，a11 和 a12 已传递）
  PE[1,0]：temp = a21 * b21，向右传递到 PE[1,1]
  PE[0,1]：temp2 = a12 * b12，和 = temp + temp2，向下传递到 PE[1,1]

周期 4：
  PE[1,1]：从上方（PE[0,1]）和左侧（PE[1,0]）累加
  最终结果：C = [[c11, c12], [c21, c22]]
  其中 c11 = a11*b11 + a12*b21, c12 = a11*b12 + a12*b22
        c21 = a21*b11 + a22*b21, c22 = a21*b12 + a22*b22
```

**2c) 各自何时优于对方：**

MXU 的优势在于：计算密集、规整，且整个计算图可以提前编译完成（Google 的生产工作负载）。与 XLA 的紧密集成使其能够进行激进的融合，最大限度地减少内存流量。

Tensor Core 的优势在于：工作负载需要动态控制流、不规则操作，或使用不通过 XLA 编译的框架（例如原生 PyTorch）。CUDA 生态系统为自定义操作提供了更多工具。

---

### 答案 3：OCS 的优势

**3a) 物理机制：**

OCS 使用 MEMS（Micro-Electro-Mechanical Systems，微机电系统）反射镜阵列。每个输入光纤的光束照射到一个微型反射镜上，该反射镜可以物理倾斜，将光线反射到特定的输出光纤。当需要改变拓扑时，调整反射镜角度（约需 10 微秒）。光信号携带与电信号相同的数据，但通过交换机时无需任何电处理——因此交换机对协议是透明的（protocol-transparent）。

**3b) 相对于固定电互联的优势：**

1. **多租户隔离**：不同租户的流量通过物理上分离的光路径传输。一个租户的大量梯度通信不会导致另一个租户的网络拥塞，而在共享的电网络中这会发生。

2. **容错性**：如果某个芯片或链路发生故障，OCS 可以在微秒级内重新路由绕过故障。在固定的 2D Torus 中，单个芯片故障会破坏环的连续性，需要复杂的软件级解决方案。

3. **资源分配灵活性**：在 OCS 之前，物理 TPU Pod（例如 256 个芯片）必须作为一个整体分配给单个任务。任何剩余芯片都不能被其他任务使用。有了 OCS，4096 芯片的 v4 Pod 可以动态分区为任意大小的子集群（例如 1024 + 1024 + 2048），不会产生碎片。

4. **能效**：光交换机的功耗与端口数成正比（而非带宽）。电交换机的功耗与带宽成正比，因此在高数据速率下，光方案效率更高。

**3c) 对任务调度的影响：**

OCS 几乎消除了碎片。考虑一个 4096 芯片的 Pod：如果一个任务需要 1000 个芯片，调度器可以精确分配 1000 个芯片，并重新配置 OCS 从这些芯片形成一个连续的 2D Torus。剩余的 3096 个芯片完全可用于其他任务。这显著提高了利用率。

对于混合工作负载：大型训练任务 + 小型推理任务可以在同一物理基础设施上共存，OCS 提供严格的性能隔离。

**3d) 局限性：**

OCS 的切换延迟（约 10 微秒）远高于电交换（纳秒级）。这使得 OCS 不适合逐消息或逐批路由。OCS 最适合于不频繁更改的电路交换拓扑（任务级调度）。对于需要在毫秒级粒度进行动态路由的工作负载，混合方法（OCS + 电包交换）可能更优。

---

### 答案 4：TPU 与 GPU 的权衡

| 场景 | 更好的选择？ | 理由 |
|----------|---------------|-----------|
| 在 1024 芯片上大批量训练稠密 Transformer（100B 参数） | TPU v4/v5p | TPU 的 2D Torus + OCS 在大规模 all-reduce 中提供接近线性的扩展效率。TPU 的 MXU 在 Transformer 层的稠密矩阵乘法方面表现出色。 |
| BERT-Large 低延迟推理（batch size=1） | GPU（例如 NVIDIA T4/L4） | TPU 针对大批量高吞吐量设计。对于 batch=1 推理，TPU 编译和存储层次结构的开销会增加延迟。GPU + TensorRT 可实现亚毫秒级延迟。 |
| 训练具有 100B 嵌入表的推荐模型 | TPU v4 | TPU v4 上的 SparseCore 专为嵌入查找（embedding lookups）而设计——这是 TPU 的独特优势。GPU 没有等效的硬件，使得嵌入成为瓶颈。 |
| 小批量训练 1B 参数 CNN 以快速原型验证 | GPU | TPU 的编译开销需要大批量来摊还。对于小批量快速原型开发，GPU 的即时执行（eager execution）和丰富的调试工具更高效。 |
| 总参数为 1T 的稀疏 MoE 模型 | TPU v4/v5p | TPU 的高带宽互联（OCS）支持 MoE 路由所需的高效 all-to-all 通信。GPU 集群在 MoE 场景中经常受限于节点间带宽。 |
| 边缘设备推理（<50W 功耗） | GPU（Jetson 系列） | TPU 是数据中心级硬件，不适用于边缘部署。NVIDIA Jetson 和其他边缘 SoC 专为此功耗范围设计。 |
| 科学计算（FP64 矩阵运算） | GPU（NVIDIA H100/A100） | TPU 针对机器学习数值格式（BF16、INT8）进行了优化。TPU 的 FP64 性能有限，而 NVIDIA GPU 拥有专用的 FP64 Tensor Core。 |
| 多模态模型训练 | TPU（如果 Google 内部）或 GPU | TPU 的优势取决于多模态模型的具体架构。如果是基于 Transformer 的模型，TPU 表现出色。如果涉及自定义操作，GPU 的灵活性更好。 |

---

### 答案 5：XLA 编译器优化

**5a) 编译阶段：**

| 阶段 | 输入 | 输出 | 关键变换 |
|-------|-------|--------|-------------------|
| HLO 构建 | 来自 TF/JAX 的高层 IR（算子图） | HLO（High Level Optimizer）IR | 将框架算子降低为 XLA 的 HLO 算子。每个算子成为一条 HLO 指令。 |
| HLO 优化 | HLO IR（未优化） | HLO IR（已优化） | 代数化简、常量折叠、死代码消除、**算子融合**、布局分配、内存分析。 |
| 并行化（SPMD Partitioner） | 优化后的 HLO | 分区后的 HLO | 在设备间复制计算，插入 all-reduce/collective ops 用于梯度同步，根据分片标注（sharding annotations）对张量进行分区。 |
| 代码生成 | 分区后的 HLO | TPU 可执行文件（底层微代码） | 将 HLO 算子降低为 TPU 专用指令。将操作分配到 MXU、VPU、SPU。调度指令流水线。管理 HBM 到 UB 的数据移动。 |

**5b) 算子融合示例：**

**不进行融合：**
1. Concatenate kernel：从 HBM 读取 x, y，将 h 写入 HBM。
2. Dot-product kernel：从 HBM 读取 W, h，将 z 写入 HBM。
3. Reduce-sum kernel：从 HBM 读取 z，将 out 写入 HBM。

**总计：3 次 kernel 启动，5 次 HBM 读/写。**

**进行融合：**
XLA 的融合 pass 将（concatenate -> dot -> reduce-sum）分组为单个融合区域。融合后的 kernel：
1. 直接从 HBM 读取 x, y, W 到 Unified Buffer（UB）。
2. 在寄存器中执行拼接（不写 HBM）。
3. 使用 MXU 执行点积（从 UB 流式传输）。
4. 在 VPU（向量单元）中执行 reduce-sum。
5. 将最终输出一次性写入 HBM。

**总计：1 次 kernel 启动，4 次 HBM 读取 + 1 次 HBM 写入。**

**5c) 融合对 TPU 的重要性：**

TPU 的存储层次结构是融合比 GPU 更重要的关键原因：
- TPU 的 Unified Buffer 有限（v4 上约 28 MB，而 GPU 有数 MB 的 L2 缓存）。
- 每次 HBM 读/写的能耗和延迟远高于 UB 访问。
- TPU **没有** GPU 拥有的复杂多级缓存层次结构（L1, L2, L3）。
- 因此，将中间结果写入 HBM 再读回的成本极高。
- 融合使编译器能够将中间值保留在 UB 中，或直接在 MXU 和 VPU 之间传递它们，而无需触碰 HBM。
- 对于 GPU，L1/L2 缓存有时可以吸收中间流量——但 TPU 需要显式的数据移动管理，这使得融合对于任何可接受的性能都至关重要。

不进行融合时，TPU 程序通常是内存带宽受限的；进行融合后，它变为 MXU 上的计算受限，可实现 80%+ 的硬件利用率。

---

## 参考文献

1. Jouppi, N. P., et al. "In-Datacenter Performance Analysis of a Tensor Processing Unit." ISCA'17.
2. Jouppi, N. P., et al. "A Scalable Architecture for Cloud TPU." ISCA'18.
3. Jouppi, N. P., et al. "TPU v4: An Optically Reconfigurable Supercomputer for Machine Learning with Hardware Support for Embeddings." ISCA'23.
4. Google Cloud TPU Documentation. "TPU System Architecture." https://cloud.google.com/tpu/docs/system-architecture.
5. Sabne, A., et al. "XLA: Optimizing Machine Learning Compiler." Google Research, 2020.
6. Mark, H., et al. "Mixed Precision Training." ICLR'18.
7. Jia, Z., et al. "Beyond Data and Model Parallelism for Deep Neural Networks." SysML'19.
8. Farrington, N., and Porter, G. "Optical Data Center Networks." ACM SIGCOMM'13.
9. NVIDIA. "Tensor Core Performance: The Ultimate Guide." NVIDIA Developer Blog.
10. Google Cloud Blog. "TPU v5p: A New Generation of Custom Machine Learning Hardware." 2024.
