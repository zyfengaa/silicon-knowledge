# 项目 02 — 多级缓存模拟器

> 实现一个 trace 驱动的 L1/L2/L3 缓存模拟器，把"命中率"拆成局部 / 全局口径，并把每次缺失换算成 AMAT 与 DRAM 流量。

## 目标

- 从单一缓存扩展到三级层次，理解包含性、写回、写分配与逐出传播。
- 能独立计算 tag / index / offset、替换受害者、脏行写回和下一级访问。
- 用可复现的 trace 比较容量、相联度、行大小、替换策略对命中率和 DRAM 流量的影响。
- 用 AMAT 把微架构参数翻译成"平均每次访问慢多少拍"。

## 前置知识

- [模块 05：存储层次](../../05-存储层次/README.md)
- [为什么需要存储层次](../../05-存储层次/notes/01-why-hierarchy.md)、[缓存基础](../../05-存储层次/notes/02-cache-basics.md)
- [缓存组织方式](../../05-存储层次/notes/03-cache-organization.md)、[缓存策略](../../05-存储层次/notes/04-cache-policies.md)
- [DRAM 基础](../../05-存储层次/notes/07-dram-basics.md)
- 参考实现：[cache_sim.c](../../05-存储层次/code/c/cache_sim.c)（单级、LRU、硬编码 trace）与 [cache_analysis.py](../../05-存储层次/code/python/cache_analysis.py)（轨迹仿真）
- 练习题：[模块 05 练习题](../../05-存储层次/exercises/05-memory-q.md)

## 任务要求

**必做**

1. C++17 或 Python 3.10+，三级缓存均支持配置总容量、相联度、行大小；启动时校验容量是 `组数 × 相联度 × 行大小`，非法参数报错退出。
2. 默认采用 **non-inclusive / non-exclusive（NINE）** 层次；L1/L2 缺失逐级向下请求，任一级缺失时按行填充。
3. 实现 **write-back + write-allocate**：写命中置脏，写缺失先取行再写；被逐出的脏行向下一级发出写回。
4. 实现真正的 LRU（命中也要更新年龄）与**固定种子**的随机替换；两者可配置。逐出时记录受害者、是否脏、来自哪一级。
5. 解析 CSV trace：`op,addr,size`，`op ∈ {R,W}`，地址 64 位；支持按指令数计算 MPKI（trace 提供 `I` 行或单独计数文件时）。
6. 统计每级 accesses / hits / misses / 局部缺失率 / 全局缺失率、逐出数、脏写回数；汇总 DRAM 读字节、写字节与总访问次数。
7. 按配置的 L1/L2/L3/DRAM 延迟计算 AMAT，写明公式与每一层的延迟口径。
8. 生成 4 类 trace：顺序、固定步长冲突、随机、分块矩阵乘；每类至少 1M 次访问。

**可选扩展**

- 实现 inclusive 层次与 L3 逐出时的反向失效（back-invalidation）。
- 加入 write-through、非写分配、伪 LRU、prefetch（next-line / stride）。
- 加入 TLB 与页大小，统计 page walk 次数。
- 用 `valgrind --tool=lackey --trace-mem=yes`（Linux）采集真实程序 trace。

## 里程碑

- **M1 骨架**：单级缓存 + trace 解析 + tag/index/offset；3 个手算 trace 通过。
- **M2 核心**：三级层次、写回 / 写分配、LRU / 随机、逐级统计与 AMAT。
- **M3 验证**：与 `cache_sim.c` 对同一 trace 的命中 / 缺失计数对齐；手算脏写回。
- **M4 报告**：参数扫描、AMAT 对比、DRAM 流量图与结论。

## 交付物

- `src/`：模拟器；`tests/`：手算 trace 与期望统计；`scripts/`：trace 生成器。
- `traces/`：4 类 trace（可用生成器复现，不必提交超大文件）；`results/`：参数扫描 CSV。
- `plots/`：命中率 vs 相联度 / 容量 / 行大小、DRAM 流量对比、AMAT 柱状图。
- `report.md`：实验设置、口径、结果、优化建议与局限。

## 验收标准

- 3 个手算 trace 的 tag/index/offset、每次命中 / 缺失、受害者行与最终缓存内容 **逐访问一致**。
- L1-only 模式下，对 `cache_sim.c` 的 22 条硬编码地址与其 4 组配置，命中 / 缺失计数与参考程序完全一致。
- 构造的写回序列中，脏行逐出与 DRAM 写次数与手算一致；干净行逐出不产生写。
- LRU 与随机替换在冲突 trace 上产生不同受害者；随机策略固定种子后重复运行结果一致。
- 参数扫描至少 12 组（容量 / 相联度 / 行大小 / 替换策略组合），每组记录局部缺失率、全局缺失率、DRAM 字节与 AMAT。
- AMAT 计算与公式手算误差 < 0.1%；报告中明确说明全局缺失率的分母和包含性口径。

## 参考

- Hennessy & Patterson, *Computer Architecture: A Quantitative Approach*, 第 2 章。
- Hill, M. D., & Smith, A. J. "Evaluating Associativity in CPU Caches." *IEEE Transactions on Computers*, 1989.
- [模块 05 参考公式与练习](../../05-存储层次/exercises/05-memory-q.md)
- [cache_sim.c](../../05-存储层次/code/c/cache_sim.c) 与 [matrix_mult_tiling.c](../../05-存储层次/code/c/matrix_mult_tiling.c)

## 常见陷阱与口径

- **局部缺失率** = 本级缺失 / 本级访问；**全局缺失率** = 本级缺失 / CPU 总访问。两者不能混用。
- 写缺失在 write-allocate 下会先产生一次下一级**读**，不要把它误记为 DRAM 写；脏行逐出才是 DRAM 写。
- LRU 在命中时也要更新时间戳；否则会退化成 FIFO，冲突 trace 上结果明显不同。
- 行大小改变 offset 位数，也改变一次缺失搬运的字节数；DRAM 字节按行计，不按请求 size 计。
- NINE 下同一行可能同时存在于多级；若实现 inclusive，L3 逐出必须反向失效 L1/L2，否则一致性口径错误。
- 随机替换必须固定种子并在报告中注明；否则实验不可复现。
- trace 的地址是字节地址；不要把字地址直接当地址分解。统计前先确认 `size` 是否跨行。
