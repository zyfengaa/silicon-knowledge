# Eyeriss: A Spatial Architecture for Energy-Efficient Dataflow

> **文献信息**
> - 会议：ISCA (International Symposium on Computer Architecture), 2016
> - 作者：Yu-Hsin Chen, Joel Emer, Vivienne Sze
> - 机构：MIT
> - 引用：Chen Y H, Emer J, Sze V. Eyeriss: A spatial architecture for energy-efficient dataflow for convolutional neural networks[C]//ACM/IEEE 43rd Annual International Symposium on Computer Architecture (ISCA), 2016: 367-379.

---

## 一、动机与背景

卷积神经网络（CNN）在图像分类、目标检测、语义分割等视觉任务中取得了突破性进展，但其计算和存储需求也急剧增长。在移动端和嵌入式场景中，能效（energy efficiency）成为核心约束——不仅需要足够的算力完成推理，更需要在有限的功耗预算内完成。然而，通用处理器（CPU/GPU）在运行CNN时存在严重的**数据搬运开销**：数据在DRAM与计算单元之间的移动能耗远超计算本身。

论文引用了Horowitz关于能耗比例的关键数据：一次DRAM访问的能耗约是一次MAC（乘加运算）的200倍，一次SRAM访问约是MAC的10倍。这意味着，**减少数据搬运次数比减少计算次数更重要**。传统加速器设计往往专注于提高吞吐量（TOPS），却忽视了数据流（dataflow）对能耗的决定性影响。

已有的数据流方案包括：
- **权重固定（Weight Stationary, WS）**：权重在PE内复用，输入特征图和部分和流动。
- **输入固定（Input Stationary, IS）**：输入特征图在PE内复用，权重和部分和流动。
- **输出固定（Output Stationary, OS）**：部分和在PE内累积，权重和输入流动。

但这三种数据流均未被系统性地在相同硬件约束下进行比较。Eyeriss的核心贡献在于：**提出了一种新的行固定（Row-Stationary, RS）数据流，并在统一框架下对所有四种数据流进行了能量建模与比较**。

---

## 二、行固定（Row-Stationary）数据流设计

行固定数据流的核心思想是：**将卷积的计算维度分解为行级别的粒度，并在PE阵列中以行为单位进行数据复用**。具体来说：

1. **权重的行复用**：每个PE负责处理一个卷积核的某一行权重。由于卷积核在同一输入特征图上滑动时，同一行权重被多次使用，RS数据流将这些权重固定在PE内部，避免重复加载。

2. **输入特征图的行复用**：输入特征图的某一行像素在同一卷积核的不同行之间也被复用。RS数据流通过精心设计的数据流动路径，使输入像素在PE之间高效传递。

3. **部分和的局部累积**：每个PE计算完一个行卷积后产生部分和，这些部分和在PE阵列内累积，最终生成完整的输出像素。累积过程不需要访问全局缓冲区。

RS数据流的关键创新在于**直接匹配卷积的计算模式**：卷积本质上是二维滑动窗口操作，行级别的复用天然适应这种模式。相比之下，WS数据流在卷积核跨输入通道时效率下降，OS数据流在输出通道数较小时难以充分利用PE。

论文通过一个形式化的能量模型证明了RS数据流在大多数CNN层配置下具有最低的能量开销。该模型将数据搬运分解为三个层次：PE内的RF访问、PE间的NoC（片上网络）访问、全局缓冲区的SRAM访问和DRAM访问，并对每种数据流的访问次数进行了精确计数。

---

## 三、片上网络（NoC）设计

Eyeriss的PE阵列采用**2D网格（mesh）拓扑**，并设计了三种独立的网络来传输不同类型的数据：

1. **全局输入总线（Global Input Bus）**：一个多播（multicast）网络，用于将输入特征图数据从全局缓冲区广播到多个PE。由于同一输入像素被多个卷积核共享，多播机制可以有效减少数据重复传输。

2. **全局输出总线（Global Output Bus）**：用于将PE计算完成的部分和或最终结果写回全局缓冲区。

3. **PE间本地网络（PE-to-PE Local Network）**：相邻PE之间的直接连接，用于在行方向上传递部分和。这是RS数据流的关键支撑——当一个PE完成某行权重的卷积后，其部分和需要传递给下一个PE以进行累积。

此外，Eyeriss的PE内部包含多个寄存器文件（RF），用于缓存权重、输入和部分和。每个PE还包含一个小的SRAM缓冲区（称为"spad"），用于在需要时暂存数据。这种层次化的存储设计（RF → PE本地SRAM → 全局SRAM → DRAM）与RS数据流紧密结合，最大限度地减少了高层级存储的访问次数。

---

## 四、评估方法与实验结果

### 评估方法

Eyeriss采用了系统化的评估框架：
- **能量模型**：基于45nm CMOS工艺的数据，对每个MAC操作及其相关的数据搬运进行能量计数。模型参数包括：RF访问能耗（1×基准）、PE间转移能耗（2×）、全局SRAM访问能耗（6×）、DRAM访问能耗（200×）。
- **工作负载**：选择了AlexNet、VGG-16和GoogleNet等代表性CNN模型的各层作为测试用例。
- **比较基线**：在同一PE阵列规模（12×14 = 168个PE）和相同工艺节点下，分别实现了WS、IS、OS和RS四种数据流。

### 主要结果

1. **RS数据流的能效优势**：在大多数层中，RS数据流的能量开销比次优的OS数据流降低1.2×~1.8×，比WS和IS降低更多。在输入通道数较大的层中（如AlexNet的conv1），优势更为明显。

2. **数据搬运占比分析**：对于RS数据流，PE内部RF访问占据了总能量的大头（约40%-60%），DRAM访问占比很小（在VGG-16的大部分层中低于10%）。相比之下，WS数据流的DRAM访问占比更高，因为输入数据无法在PE内有效复用。

3. **吞吐量与能效的平衡**：RS数据流在不牺牲吞吐量的前提下提高了能效。PE利用率和WS数据流相当。

4. **与GPU对比**：在相同功耗预算下，Eyeriss达到了比移动GPU高一个数量级以上的能效（GOPS/W），但绝对性能（GOPS）低于高端桌面GPU。

---

## 五、后续工作与影响

Eyeriss团队后续在JSSC上发表了芯片实现结果：
- **Eyeriss v1** (JSSC 2017)：65nm CMOS工艺，168个PE，16位定点精度，在200MHz下达到34.7FPS/W（AlexNet），能效比当时的移动GPU高10倍以上。
- **Eyeriss v2** (JSSC 2019)：加入了稀疏性支持，利用行压缩编码（CCSR）跳过零值计算，进一步提升了能效。

Eyeriss的RS数据流已被广泛引用于后续的NPU/NPU设计中。其提出的**数据流能量分析框架**已成为DNN加速器设计的标准方法论，被后续研究工作（如Eyeriss v2、MAERI、NVDLA等）采纳和扩展。论文获得了HPCA 2021的Test of Time Award。

---

## 六、思考与启示

1. **数据搬运才是能耗的根本矛盾**：Eyeriss深刻揭示了"计算快不等于能效高"的道理，在DNN加速器设计中，存储层次和数据流设计比纯计算单元设计更重要。

2. **专用化的边界**：RS数据流高度适配CNN的卷积模式，但对于全连接层和逐元素操作效率下降。这提示我们在设计加速器时需要在专用性和通用性之间权衡。

3. **数据流与硬件结构应协同设计**：RS数据流并非凭空产生，而是与PE阵列的NoC结构、存储层次深度耦合。这种协同设计（co-design）的思路是体系结构创新的重要范式。

4. **方法论贡献大于工程贡献**：Eyeriss最大的贡献可能不是RS数据流本身，而是建立了一套系统的数据流能量比较框架。这种"给出对比方法论"的工作方式值得学习。

---

## 参考文献

1. Chen Y H, Emer J, Sze V. Eyeriss: A spatial architecture for energy-efficient dataflow for convolutional neural networks[C]//2016 ACM/IEEE 43rd Annual International Symposium on Computer Architecture (ISCA). IEEE, 2016: 367-379.

2. Chen Y H, Krishna T, Emer J S, et al. Eyeriss: An energy-efficient reconfigurable accelerator for deep convolutional neural networks[J]. IEEE Journal of Solid-State Circuits (JSSC), 2017, 52(1): 127-138.

3. Chen Y H, Yang T J, Emer J, et al. Eyeriss v2: A flexible accelerator for emerging deep neural networks on mobile devices[J]. IEEE Journal on Emerging and Selected Topics in Circuits and Systems (JETCAS), 2019, 9(2): 292-308.

4. Horowitz M. Computing's energy problem (and what we can do about it)[C]//2014 IEEE International Solid-State Circuits Conference (ISSCC). IEEE, 2014: 10-14.

5. Sze V, Chen Y H, Yang T J, et al. Efficient processing of deep neural networks: A tutorial and survey[J]. Proceedings of the IEEE, 2017, 105(12): 2295-2329.

6. Jouppi N P, Young C, Patil N, et al. In-datacenter performance analysis of a tensor processing unit[C]//2017 ACM/IEEE 44th Annual International Symposium on Computer Architecture (ISCA). ACM, 2017: 1-12.
