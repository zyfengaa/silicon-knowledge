# 论文笔记：TAGE-SC-L 分支预测器

## 论文信息

- **标题:** TAGE-SC-L Branch Predictors
- **作者:** Andre Seznec (Inria)
- **发表于:** Journal of Instruction-Level Parallelism (JILP), 2014

## 其他参考文献

- Seznec, A. & Michaud, P. "A Case for (Partially) Tagged Geometric History Length Branch Prediction." *JILP*, 2006. (Original TAGE proposal)
- Yeh, T.-Y. & Patt, Y. N. "Two-Level Adaptive Training Branch Prediction." *MICRO-24*, 1991.
- Seznec, A. "The L-TAGE Branch Predictor." *JILP*, 2007.

## 一句话贡献

TAGE（带标签的几何历史长度，Tagged Geometric History Length）通过组合多个以几何级数递增的历史长度进行索引的预测器表（predictor table），并使用带标签的条目（tagged entry）来消解冲突，从而实现了接近最优的分支预测（branch prediction）准确率——对 CINT 通常超过 95%，对 CFP 超过 90%——同时将存储控制在实用范围内（例如，锦标赛级配置为 32 Kbits）。

## 背景：为什么我们需要更好的分支预测

现代超标量处理器（superscalar processor）会在深流水线（15--25 级）上每周期发射多条指令。每个分支——大约每五到六条指令中就有一个——都可能在前端（front-end）等待结果解析期间造成停顿。一次误预测（misprediction）的**周期代价**大约是从取指到分支结果解析的流水线深度（再加上流水线重新填充，refill）；**被浪费的指令槽（instruction slot）**则是该周期数乘以发射宽度（issue width）。因此，在一台 4 宽、20 级流水线的机器上，单次误预测可能浪费大约 80 个指令槽的潜在工作（当然，这些槽未必都能被有效填满）。

早期分支预测器（branch predictor）使用简单的 2 位饱和计数器（saturating counter，Smith，1981），它们能捕获分支的偏向性（例如总是跳转或大多数时候跳转），但对于具有周期性或上下文相关行为的分支则无能为力。两级自适应预测器（two-level adaptive predictor，Yeh & Patt，1991）通过跟踪近期分支的结果（即*全局历史（global history）*）并利用该模式索引计数器表，提高了准确率。然而，当不同分支在预测器表中相互干扰时，这些预测器仍然力不从心，这个问题被称为*别名（aliasing）*。

TAGE 背后的关键洞见在于：不同分支受益于不同长度的历史。一个循环闭合分支（loop-closing branch）可能只需要 4--8 位历史就能被完美预测，而深陷于嵌套条件分支内部的分支可能需要 100 位以上的历史。TAGE 在单一且存储高效的设计中兼顾了这两个极端——以及介于两者之间的所有情况。

## 关键概念

### 带标签的几何历史长度（Tagged Geometric History Lengths）

TAGE 维护多个预测器表（predictor table），每个表关联一种不同的历史长度。这些长度按几何级数增长：如果最短的表使用 L 位历史，那么下一个使用约 2L，再下一个使用约 4L，依此类推。例如，一个典型的 32-Kbit TAGE 配置可能使用 4、8、16、32、64、128 和 256 位的历史长度。

这种几何级数增长是有意为之：它用少量表覆盖了很大范围的相关距离（correlation distance）。线性增长（例如 2、4、6、8、...）要达到相同的最大历史长度则需要多得多的表，从而消耗更多面积和访问能耗。

### TAGE 表

每个 TAGE 表都是一个直接映射（direct-mapped）的条目数组。每个条目包含：

1. **一个饱和计数器**（通常为 3 位）：预测分支方向（跳转 / 不跳转）。
2. **一个标签（tag）**（通常为 8--12 位）：分支 PC 与全局历史的哈希值。标签用于验证该条目确实对应当前的“分支—历史”组合。
3. **一个有用位（useful bit）**（1 位）：指示该条目最近是否贡献过有用的预测，供替换策略（replacement policy）使用。

当预测一个分支时，所有表会被并行读取。预测结果由*产生标签匹配的最长历史表*给出。如果没有任何表匹配，则由基础预测器（base predictor，一个由 PC 索引的简单 2 位计数器）提供默认预测。这种“最长匹配获胜”（longest-match-wins）策略是 TAGE 的核心：短历史表处理常见模式，而长历史表捕获稀有但高度相关的上下文。

### 为什么更长的历史能提高预测准确率

考虑一个位于三层嵌套循环深处的分支。它的结果可能取决于数百条指令之前的分支历史。具有固定且较短历史窗口的两级预测器无法捕获这种相关性。TAGE 最长的表可以做到，因为它们使用 128 位或 256 位全局历史进行索引。

反过来，短历史表处理那些结果仅依赖于最近几个分支的分支——例如，在短行程和长行程之间交替的循环的回边（back-edge）。对此类分支使用长历史会引入噪声（不相关的历史位）并增加表冲突。TAGE 通过标签匹配机制自动选择适当的长度。

## 资源效率

TAGE 最令人印象深刻的成就是其准确率与存储之比。在 2014 年冠军分支预测（Championship Branch Prediction，CBP）评测中，一个 32-Kbit 的 TAGE 配置在 CINT 基准测试上取得了低于每 1000 条指令 4 次误预测（4 MPKI）的误预测率——超过了规模大得多的预测器：

以下数字仅作示意：MPKI 在很大程度上取决于基准测试套件、预测器配置和统计方法，因此应将其视为数量级参考，而非精确结果。

| 预测器类型              | 存储预算      | MPKI（CINT 平均值） |
|-------------------------|---------------|-------------------|
| 2 位双模态              | 4 Kbits       | ~12               |
| Gshare（8 Kbits）       | 8 Kbits       | ~8                |
| 锦标赛（Alpha 21264）   | 16 Kbits      | ~6                |
| **TAGE（32 Kbits）**    | **32 Kbits**  | **~3.5**          |
| 大型 TAGE（256 Kbits）  | 256 Kbits     | ~2.0              |

这种高效源于三项设计选择：

1. **带标签的条目与几何历史**——表只为那些确实表现出相关性的“分支—历史”组合存储条目。不相关的组合以近乎零的存储代价获得基础预测。
2. **直接映射组织**——每个表都是一个简单数组，使访问延迟保持在较低水平（单周期），且面积较小。无需相联查找（associative lookup）或复杂索引。
3. **有用位替换**——当必须分配新条目时，预测器倾向于逐出有用位为零的条目（即最近没有贡献过正确预测的条目）。这可防止抖动（thrashing）。

### “-SC-L”扩展

完整的 TAGE-SC-L 预测器还增加了可选组件：

- **SC（统计校正器，Statistical Corrector）**：一个辅助预测器（side predictor），用于校正 TAGE 对那些极难预测分支的预测。它使用一张大表，该表由 PC 与全局历史的哈希值索引，存储按置信度加权的校正量。只有当 TAGE 的置信度较低时，才会查询 SC。
- **L（循环预测器，Loop predictor）**：一个专用组件，用于检测并预测具有恒定迭代次数的循环。对于遵循固定的“跳转 N 次、跳过 1 次”模式的分支，它会覆盖 TAGE 的预测。

这些扩展会增加约 10% 的存储，但在循环密集型工作负载上可将误预测再减少 15--25%。

## 我的思考

### 我学到了什么

TAGE 改变了我对预测器设计的看法。早期的预测器（双模态、gshare、锦标赛）统一对待所有分支：每个“分支—历史”对都映射到一个预测计数器。TAGE 的核心洞见——分支与不同“距离”的历史相关，并且我们应当通过标签让每个分支找到其自身的最佳距离——既优雅又实用。

几何历史长度递增是一种巧妙的工程权衡。它对任何单个分支都不是最优的，但能在整个谱系上提供良好的覆盖。其结果是一种既简单到足以在硬件中实现（通过直接映射表进行单周期访问），又精确到足以逼近基于历史的预测理论极限的预测器。

### 与其他主题的联系

- **存储层次（memory hierarchy）**：TAGE 的标签加数据组织方式类似于组相联缓存（set-associative cache），但其索引依据是（PC，全局历史）而不是地址。有用位替换策略与缓存中的伪 LRU（pseudo-LRU）相呼应。
- **乱序执行（out-of-order execution）**：准确的分支预测是宽而深流水线的前提条件。如果没有 TAGE 级别的准确率，误预测代价就会主导现代超标量处理器的性能。
- **机器学习（machine learning）**：TAGE 可以被视为一种集成学习（ensemble learning）：多个弱预测器（各个表中的计数器）通过一种优先级方案（最长匹配获胜）组合起来。SC 组件则在此基础上增加了一个元学习器（meta-learner）。

### 开放问题

1. **收益递减（diminishing returns）**：将历史长度从 256 位翻倍到 512 位是否仍能显著提高准确率，还是说我们已经触及大多数分支的相关性极限？
2. **神经预测器（neural predictors）**：基于感知机（perceptron）的预测器（Jimenez & Lin，2001）表明，学习到的权重可以补充历史表。未来的商用预测器会进一步转向学习模型，还是 TAGE 的简洁性和可验证性会使它继续在商用核心中占据主导地位？
3. **功耗（power）**：TAGE 每个周期都并行读取多个表。在 7--8 个表的情况下，这种能耗代价不可忽视。我们能否设计一种先只激活最有可能匹配的那个或那些表的预测器？

### 今日相关性（2026）

基于 TAGE 的预测器仍然是商用处理器中的主流设计点。据报道，许多高性能核心使用类似 TAGE 的多表预测器：AMD 的 Zen 系列和 Intel 的近期核心通常被分析为源自 TAGE，而 Arm 的 Cortex-X 系列据信采用了类似 TAGE 的设计。然而，厂商并不公布完整的预测器细节，因此具体的归因应被视为有依据的分析，而非已确认的事实。核心设计已经过改进（更大的表、更好的哈希函数、改进的 SC 组件），但基本架构——几何历史、带标签的条目、最长匹配获胜——已被证明具有非凡的生命力。

---

## 参考文献

1. Seznec, A. "TAGE-SC-L Branch Predictors." *Journal of Instruction-Level Parallelism*, Vol. 16, 2014, pp. 1--13.
2. Seznec, A. & Michaud, P. "A Case for (Partially) Tagged Geometric History Length Branch Prediction." *JILP*, Vol. 8, 2006.
3. Yeh, T.-Y. & Patt, Y. N. "Two-Level Adaptive Training Branch Prediction." *Proceedings of MICRO-24*, 1991, pp. 51--61.
4. Seznec, A. "The L-TAGE Branch Predictor." *JILP*, Vol. 9, 2007.
5. Smith, J. E. "A Study of Branch Prediction Strategies." *Proceedings of ISCA-8*, 1981, pp. 135--148.
6. Jimenez, D. A. & Lin, C. "Dynamic Branch Prediction with Perceptrons." *Proceedings of HPCA-7*, 2001.
7. Hennessy, J. L. & Patterson, D. A. *Computer Architecture: A Quantitative Approach*. 6th Edition. Morgan Kaufmann, 2019. Chapter 3.
