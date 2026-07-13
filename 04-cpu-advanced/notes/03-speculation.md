# 03 — 推测执行（Speculative Execution）

## 概述

推测执行是乱序超标量处理器的自然延伸。当处理器遇到分支指令时，它不等待分支条件就绪，而是**猜一个方向继续执行**。如果猜对了，节省了等待时间；如果猜错了，必须回滚。

> 推测执行的核心假设：**适当的错误成本远低于等待的成本**。

## 推测执行的基本流程

```
取指 → 分支预测 → 推测性发射 → 验证 → 提交或回滚
```

### 三步走

1. **预测（Predict）**：分支预测单元（BPU, Branch Prediction Unit）给出预测方向及目标地址
2. **推测执行（Speculatively Execute）**：处理器沿着预测路径执行指令，结果暂时保存在 ROB 中，未被提交
3. **验证（Verify）**：当分支条件最终计算出真实结果时，比较预测与真实
   - 预测正确：ROB 中的指令被标记为非推测态，正常提交
   - 预测错误：**误预测恢复（Misprediction Recovery）**

## 误预测恢复（Misprediction Recovery）

当分支预测错误时：

1. **清空 ROB**：删除该分支之后的所有 ROB 条目
2. **恢复寄存器映射表（RAT）**：恢复到分支点的映射状态（通常通过 RAT 检查点/快照实现）
3. **刷新流水线**：清空取指、译码、发射等阶段的所有后续指令
4. **跳转到正确路径**：从正确的分支目标重新取指

### 误预测代价

误预测代价 = 清空流水线的周期数

```
误预测代价 = (分支执行阶段的流水线深度) × 发射宽度
```

示例：
- 假设流水线深度 15 级，发射宽度 4
- 一次误预测浪费约 15 × 4 = 60 条指令的进度
- 假设误预测率 2%，每条分支执行后平均有 5 条指令提交
- 性能损失 ≈ 5% ~ 15%

这就是为什么现代 CPU 投入大量资源（面积、功耗）来降低误预测率。

## 多级推测

现代处理器支持**多级推测**：在一条推测路径中遇到新的分支，可以再次推测。

```
if (cond1) {
    // 第 1 级推测路径
    if (cond2) {
        // 第 2 级推测路径（在 cond1 结果未知时推测）
        if (cond3) {
            // 第 3 级推测路径
        }
    }
}
```

- 支持多级推测的处理器需要在 ROB 中为每条指令标记其推测深度
- 回滚时只需清空深度大于或等于误预测分支深度的指令
- Apple M1 Firestorm 的支持深度：推测深度不小于分支条件计算路径长度

## 推测执行的其他形式

### 1. 加载推测（Load Speculation）

- 加载指令可以在前面的存储地址未知时推测执行
- **存储转发推测（Store-to-Load Forwarding）**：推测性地将前一个存储的值转发给后面的加载
- 如果推测错误（地址冲突），需要重新加载

### 2. 预测执行（Predicate Speculation）

- 在某些架构（如 ARM Cortex-A 系列）中，使用条件执行而不是分支
- 条件指令（如条件 move, conditional select）可以推测性写入，利用合并机制（如 flag renaming）实现

## 安全影响：Spectre 与 Meltdown

推测执行虽然对性能至关重要，但它也引入了严重的安全漏洞。

### Spectre（幽灵漏洞）

**发现时间**：2018 年 1 月（Kocher et al.）
**原理**：利用分支预测器对推测路径的"训练"能力

```
// Spectre v1（边界检查绕过）
if (x < array1_size) {
    // 如果 x 被训练为总是小于，但在最后一次被设置成恶意值
    value = array2[array1[x] * 256];  // 推测执行中会加载数据
}
```

- 当 x 被设置成越界值但分支预测器预测"taken"时
- 推测执行中越界读取 array1[x]，然后用这个值去访问 array2
- array2 的对应缓存行被加载到缓存中
- 通过测量 array2 各元素的访问时间来推断被读取的秘密数据

### Meltdown（熔断漏洞）

**原理**：利用乱序执行中权限检查的时序窗

```
// 用户态代码
value = kernel_data[offset];    // 权限检查失败 → 异常
variable = probe_array[value];  // 乱序执行已经在推测中访问了 probe_array
```

- 乱序执行在异常处理之前已经执行了后面的指令
- 虽然最终会触发异常并回滚，但缓存状态已被改变
- 通过缓存侧信道可以恢复数据

### 缓解措施

- **LFENCE 屏障指令**：阻止推测执行越过屏障（Spectre v1 缓解）
- **KPTI（Kernel Page Table Isolation）**：用户态地址空间中不映射内核页（Meltdown 缓解）
- **Retpoline**：用 return 指令序列替代间接分支（Spectre v2 缓解）
- 这些缓解措施通常带来 2% ~ 30% 的性能损失

## 推测执行的设计挑战

| 挑战 | 描述 | 解决方案 |
|------|------|---------|
| 推测状态管理 | 推测指令修改寄存器/内存状态 | ROB + 写缓冲 |
| 精确异常 | 推测路径上的异常不能传播 | ROB flush + 异常推迟 |
| 存储转发冲突 | 推测加载可能拿到错误数据 | 加载/存储次序检测 |
| 侧信道泄露 | 推测操作影响微架构状态 | 推测隔离（贵）或软件缓解 |
| 能量浪费 | 误路径消耗大量能量，机器死循环    | 功率门控 + 推测深度限制 |

## 关键概念总结

- **推测执行**：在分支条件未就绪时，基于预测继续执行
- **误预测恢复**：清空 ROB、恢复寄存器映射、刷新流水线
- **多级推测**：在推测路径中支持多级嵌套推测
- **Spectre/Meltdown**：推测执行中微架构状态的侧信道泄露

## 思考题

1. 为什么推测执行的"错误路径上的指令不能提交"是一条硬性要求？
2. 误预测代价随流水线深度和发射宽度如何变化？假设流水线 20 级、发射宽度 6，一次误预测浪费多少条指令？
3. Spectre v1 的缓解措施 LFENCE 为什么能阻止推测执行？它的机理是什么？

## 参考文献

- Hennessy, J. L. & Patterson, D. A. *Computer Architecture: A Quantitative Approach*, 6th Edition, Chapter 3: Instruction-Level Parallelism and Its Exploitation.
- Kocher, P. et al. "Spectre Attacks: Exploiting Speculative Execution." *IEEE S&P*, 2019.
- Lipp, M. et al. "Meltdown: Reading Kernel Memory from User Space." *USENIX Security*, 2018.
- Hwu, W. W. & Patt, Y. N. "Checkpoint Repair for Out-of-Order Execution Machines." *ISCA*, 1987.
- McKeeman, W. M. "The Cost of Branch Misprediction." *IEEE Micro*, 2020.
