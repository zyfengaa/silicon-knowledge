# TVM Demo: ONNX 模型编译与推理

## 概述

本演示展示如何使用 Apache TVM 将 ONNX 模型编译并部署到 CPU 或 GPU 上。TVM 是端到端的深度学习编译器栈，支持从多种框架导入模型、进行图级别和算子级别优化、并生成高效的目标代码。

## TVM 编译流水线

```
ONNX Model (.onnx)
    ↓
from_onnx() 导入
    ↓
Relay IR (图级别IR)
    ↓
图优化 (FuseOps, LayoutTransform, FoldConstant)
    ↓
TIR (张量IR, 循环级表示)
    ↓
AutoTVM / AutoScheduler (搜索最优调度)
    ↓
代码生成 (LLVM / CUDA / OpenCL)
    ↓
runtime module (可执行)
```

## 示例：编译 ResNet-18

### 步骤 1：导出 ONNX 模型

```python
import torch
import torchvision

model = torchvision.models.resnet18(pretrained=True)
dummy_input = torch.randn(1, 3, 224, 224)

torch.onnx.export(
    model, dummy_input,
    "resnet18.onnx",
    input_names=["input"],
    output_names=["output"],
    opset_version=11
)
```

### 步骤 2：导入到 TVM Relay

```python
import tvm
from tvm import relay

onnx_model = onnx.load("resnet18.onnx")
mod, params = relay.frontend.from_onnx(onnx_model, shape_dict={"input": (1, 3, 224, 224)})
```

### 步骤 3：图优化

```python
# 应用图优化 passes
mod = relay.transform.FuseOps()(mod)
mod = relay.transform.FoldConstant()(mod)
```

### 步骤 4：构建（编译为目标代码）

```python
target = "llvm"  # 或 "cuda", "opencl"
with tvm.transform.PassContext(opt_level=3):
    lib = relay.build(mod, target=target, params=params)
```

### 步骤 5：部署运行

```python
# 创建运行时环境
dev = tvm.device(str(target), 0)
module = tvm.contrib.graph_executor.GraphModule(lib["default"](dev))

# 设置输入并运行
import numpy as np
input_data = np.random.randn(1, 3, 224, 224).astype("float32")
module.set_input("input", input_data)
module.run()

# 获取输出
output = module.get_output(0).numpy()
```

## AutoTVM：自动调优

TVM 提供 AutoTVM 框架自动搜索最优调度参数：

```python
import tvm.auto_scheduler

# 定义搜索任务
tasks, task_weights = tvm.auto_scheduler.extract_tasks(mod["main"], params, target)

# 创建调优器并运行搜索
tuner = tvm.auto_scheduler.TaskScheduler(tasks, task_weights)
tuner.tune(tvm.auto_scheduler.LocalBuilder(), 
           tvm.auto_scheduler.LocalRunner(timeout=30), 
           n_trials=1000)
```

## 关键优化

### 算子融合

TVM 自动将 Conv2D + BiasAdd + ReLU 融合为单个 kernel，显著减少内存访问：

```
融合前：conv → write → bias_add → write → relu → write（3次读写）
融合后：conv → relu（1次写入，中间数据在寄存器中）
```

### 记忆化（Memory Planning）

自动分析张量生命周期，进行内存共享和复用。

## 系统要求

```bash
pip install tvm apache-tvm onnx torchvision numpy
```

## 更多资源

- [TVM 官方文档](https://tvm.apache.org/docs/)
- [TVM GitHub](https://github.com/apache/tvm)
- [Relay 前端文档](https://tvm.apache.org/docs/arch/relay.html)

## 参考文献

- Chen, T. et al. "TVM: An Automated End-to-End Optimizing Compiler for Deep Learning." *OSDI'18*.
- Zheng, L. et al. "Ansor: Generating High-Performance Tensor Programs for Deep Learning." *OSDI'20*.
- Apache TVM 官方文档. https://tvm.apache.org/docs/
