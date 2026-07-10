# Silicon Knowledge 写作规范

## 基本原则

### 📚 所有内容必须有据可查

> **严禁凭空编写。** 每篇笔记/文章的内容必须基于以下来源：
> - 权威教科书（如 Patterson & Hennessy、Kirk & Hwu 等）
> - 官方技术文档（Intel/AMD/NVIDIA/ARM/Google 白皮书）
> - 顶级会议论文（ISCA/MICRO/HPCA/ASPLOS/SC）
> - 知名技术博客（如 RISC-V 官方博客、Google AI Blog、NVIDIA Developer Blog）
> - 公开课程材料（MIT 6.004、UC Berkeley CS152/CS252、CMU 15-418 等）

### 🔗 参考文献规范

**每篇文章末尾必须包含 `## 参考文献` 章节**，格式如下：

```markdown
## 参考文献

1. Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design RISC-V Edition*. Morgan Kaufmann, 2021. — 第4章 流水线
2. [RISC-V Instruction Set Manual](https://riscv.org/technical/specifications/) — 基础指令集规范
3. Smith, J. E. "A Study of Branch Prediction Strategies." *ISCA'81*. — 分支预测经典论文
```

- 书籍引用：作者、书名、出版社、年份、相关章节
- 论文引用：作者、标题、会议/期刊名、年份
- 网络资源：链接 + 访问日期（可选）
- 每一条参考文献注明**文中哪些内容引用了它**（如"— 第X章"或"— 用于说明XX概念"）

### ❌ 不接受的来源

- 未注明出处的博客文章
- 中文培训机构/面试题的二手总结
- 明显过时的技术资料（除非用来说明历史演进）

---

## 文档结构规范

### 笔记（notes/ 下的文件）

每个 `.md` 笔记遵循以下结构：

```markdown
# 标题

## 为什么讲这个
[2-3 句话说明这个概念在整个体系中的位置和意义]

## 核心概念
[分点或分段阐述]

## 关键图示
[此处应有图——至少用 ASCII/表格描述，后续替换为正式图片]

## 深入理解
[更深入的技术细节、数学推导或实现要点]

## 总结
[3-5 句话回顾核心观点]

## 参考文献
[按上述规范列出]
```

### 代码（code/ 下的文件）

每个源文件顶部必须包含注释块：

```python
"""
文件名： systolic_sim.py
描述：   一维脉动阵列的矩阵乘模拟器。
        演示数据如何在 PE 之间流动，以及不同数据流策略的差异。
运行：   python systolic_sim.py
输出：   打印脉动阵列各 PE 的中间值和最终结果。
参考：   [H.T. Kung, "Systolic Array", 1982]
"""
```

### 图表（diagrams/ 下的文件）

- 源文件放 `diagrams/src/`，导出 PNG 放 `diagrams/png/`
- 图中使用统一的配色方案
- 关键路径标注数据宽度（如 64-bit）和延迟（如 1 cycle）

---

## 命名与格式

### 文件命名

- 目录和文件名：全小写英文，连字符分隔（`memory-hierarchy`，`cache-organization.md`）
- 笔记编号：`01-topic-name.md`（前导数字表示推荐阅读顺序）
- 代码文件：标准扩展名（`.c` `.cu` `.py` `.s`）

### Markdown 格式

- 一级标题：`#`（仅文件标题使用）
- 二级标题：`##`（主要章节）
- 三级标题：`###`（子章节）
- 代码块标注语言：\`\`\`python / \`\`\`c / \`\`\`asm
- 术语第一次出现时**加粗**，并在括号内标注英文：**流水线（Pipeline）**
- 关键数字/指标使用表格呈现

### 中英文混排

- 中文与英文/数字之间加空格（"5 段流水线" 而非 "5段流水线"）
- 英文术语第一次出现时给出中文翻译，后续可直接使用英文
- 专有名词保持原大小写（RISC-V、CUDA、Tensor Core）

---

## 内容质量检查清单

提交/合并笔记前，自查：

- [ ] 每节内容都有对应的参考文献吗？
- [ ] 参考文献涵盖所有关键主张吗？
- [ ] 代码可以运行并得到预期输出吗？
- [ ] 所有的图都有标注和说明吗？
- [ ] 练习题的答案是否正确？
- [ ] 术语是否在 GLOSSARY.md 中有对应条目？

---

## 许可证

本仓库所有原创内容采用 [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) 协议。
引用的代码和摘录遵循各自原作者的许可证。
