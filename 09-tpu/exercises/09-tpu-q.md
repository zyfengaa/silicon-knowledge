# Module 09 — TPU Exercises

---

## Question 1: TPU Generation Comparison Table

Create a detailed comparison table for TPU generations v1, v2, v3, v4, and v5p. Fill in the following dimensions for each generation. If a specific value is not publicly available, mark it as "N/A" and provide an estimate or range based on the available literature.

| Dimension | v1 | v2 | v3 | v4 | v5p |
|-----------|----|----|----|----|-----|
| MAC count | | | | | |
| On-chip memory | | | | | |
| DRAM/HBM capacity | | | | | |
| DRAM/HBM bandwidth | | | | | |
| INT8 TOPS | | | | | |
| BF16 TFLOPS | | | | | |
| Die TDP | | | | | |
| Inter-chip interconnect | | | | | |

**Questions to answer after completing the table:**
1. Which generation had the largest relative performance improvement over its predecessor?
2. What is the trend in interconnect design across generations?
3. Why did Google switch from DDR (v1) to HBM (v2+)?

---

## Question 2: MXU vs Tensor Core

Compare and contrast Google's MXU (Matrix Multiply Unit, used in TPUs) and NVIDIA's Tensor Core.

**2a)** Describe the fundamental differences in implementation between the two architectures:
- How does each compute a matrix multiply?
- What are the precision support differences?
- How programmable are they from the software perspective?

**2b)** Draw a simple state diagram (in text/ASCII art or flowchart notation) showing how a 2x2 MXU systolic array computes:
```
C = A x B
```
Where:
- A = [[a11, a12],
        [a21, a22]]
- B = [[b11, b12],
        [b21, b22]]

Trace the multi-cycle data flow through the array, showing the value in each processing element (PE) at each cycle.

**2c)** In what scenarios would MXU's systolic array approach outperform Tensor Cores, and vice versa?

---

## Question 3: OCS Advantages

Explain how Optical Circuit Switches (OCS) enable reconfigurable topology in TPU v4.

**3a)** Describe the physical mechanism of OCS (MEMS mirror arrays) and how signals are routed.

**3b)** List and explain at least 4 advantages of optical switching over fixed electrical interconnects (such as TPU v2/v3's 2D Torus or NVIDIA's NVLink):

1. Multi-tenant isolation
2. Fault tolerance
3. Resource allocation flexibility
4. Power efficiency

**3c)** How does OCS affect training job scheduling in a large datacenter? Consider:
- Fragmentation avoidance
- Job packing efficiency
- Mixed workload support (small vs large jobs)

**3d)** What are the limitations of OCS? When would a fixed electrical interconnect still be preferable?

---

## Question 4: TPU vs GPU Tradeoffs

For each of the following workload scenarios, determine whether a TPU or a GPU would be more suitable, and explain your reasoning in 2-3 sentences.

| Scenario | Better choice? | Reasoning |
|----------|---------------|-----------|
| Large-batch training of dense Transformer (100B params) on 1024 chips | | |
| Low-latency inference of BERT-Large (batch size=1) | | |
| Training a recommendation model with 100B embedding table | | |
| Small-batch training of a 1B-parameter CNN for rapid prototyping | | |
| Sparse mixture-of-experts (MoE) model with 1T total parameters | | |
| Inference on edge device with <50W power budget | | |
| Scientific computing (FP64 matrix operations) | | |
| Training a multi-modal model combining vision, text, and audio | | |

---

## Question 5: XLA Compiler Optimization

Trace the compilation path from a high-level model (TensorFlow or JAX) to a TPU executable. Each stage processes the computation graph differently.

**5a)** For each compilation stage below, describe its input, output, and the key transformations it performs:

| Stage | Input | Output | Key transformations |
|-------|-------|--------|-------------------|
| HLO Building | | | |
| HLO Optimization | | | |
| Parallelization (SPMD Partitioner) | | | |
| Code Generation | | | |

**5b)** Operator Fusion Example:

Consider the following computation:
```
h = jnp.concatenate([x, y])
z = jnp.dot(W, h)
out = jnp.sum(z, axis=1)
```

Without fusion, how many kernel launches would XLA produce? With fusion, how many kernel launches would XLA produce? Trace the fusion process step by step.

**5c)** Why is operator fusion especially important for TPU performance (more so than for GPU)? Hint: think about the memory hierarchy and the role of the Unified Buffer / HBM.

---

## Answer Key

### Answer 1: TPU Generation Comparison Table

| Dimension | v1 | v2 | v3 | v4 | v5p |
|-----------|----|----|----|----|-----|
| MAC count | 65,536 (INT8) | 32,768 (BF16 per MXU, 2 MXU) | 65,536 (BF16 per MXU, 4 MXU) | ~131K (BF16, 4 MXU per core, 2 cores) | ~262K (estimated) |
| On-chip memory | 28 MB UB + 4 MB FIFO | ~12 MB (register+cache) | ~30 MB (estimated) | ~44 MB (estimated) | ~60 MB (estimated) |
| DRAM/HBM capacity | 8 GB DDR3 | 16 GB HBM | 32 GB HBM | 32 GB HBM | 95 GB HBM |
| DRAM/HBM bandwidth | ~34 GB/s (DDR3) | ~600 GB/s | ~900 GB/s | ~1200 GB/s | ~1600 GB/s (estimated) |
| INT8 TOPS | 92 TOPS | N/A (primarily BF16) | N/A | ~275 TOPS | ~500 TOPS (estimated) |
| BF16 TFLOPS | N/A | 45 TFLOPS | 123 TFLOPS | 275 TFLOPS | 459 TFLOPS |
| Die TDP | 75 W | 280 W | 450 W | ~400 W (estimated) | ~400 W (estimated) |
| Inter-chip interconnect | PCIe Gen3 x16 | 2D Torus (custom) | 2D Torus (custom) | OCS (optical) + 2D Torus | OCS + 2D Torus |

**Answers to follow-up questions:**

1. TPU v3 had the largest relative improvement over v2 (roughly 2.7x BF16 TFLOPS) per chip. The transition from v1 to v2 also represented a massive architectural shift (inference to training).

2. Interconnect trends: PCIe (standalone) to custom 2D Torus (tightly coupled) to OCS + Torus (reconfigurable). Each generation moves toward more scalable and flexible networking.

3. DDR3 is sufficient for inference but lacks the bandwidth needed for training. Training requires frequent read/write of activations and gradients during forward/backward passes, making HBM's high bandwidth essential.

---

### Answer 2: MXU vs Tensor Core

**2a) Fundamental differences:**

- **Implementation**: MXU is a pure systolic array -- data flows in a rhythmic wave through processing elements, minimizing register file access. Tensor Cores are structured as a warp-level matrix multiply-add unit that operates on fragments of matrices loaded into registers.

- **Precision**: MXU natively supports BF16 input with FP32 accumulate. Tensor Cores support FP16, BF16, TF32, INT8, INT4, and FP64 (depending on GPU generation).

- **Programmability**: MXU is controlled entirely by XLA compiler -- no direct programmer access. Tensor Cores can be accessed via cuBLAS, cuDNN, CUDA C++ (wmma API), and Triton, offering more flexibility.

**2b) Systolic array state diagram for 2x2 MXU (C = A x B):**

```
Weights (B) are pre-loaded:
  PE[0,0] stores b11    PE[0,1] stores b12
  PE[1,0] stores b21    PE[1,1] stores b22

Cycle 1:
  Input a11 enters from left.
  PE[0,0]: temp = a11 * b11, partial sum = temp, passes right to PE[0,1]
  PE[0,1]: receives temp, stores temporarily
  PE[1,0], PE[1,1] idle

Cycle 2:
  Input a12 enters from left.
  PE[0,0]: temp = a12 * b11, partial sum = temp, passes right to PE[0,1]
  PE[0,1]: temp2 = a11 * b12, sum = temp + temp2, passes down to PE[1,1]
  Input a21 enters from top-left.
  PE[0,0] also passes a21 down to PE[1,0]

Cycle 3:
  PE[0,0]: (no new input, a11 and a12 already passed)
  PE[1,0]: temp = a21 * b21, passes right to PE[1,1]
  PE[0,1]: temp2 = a12 * b12, sum = temp + temp2, passes down to PE[1,1]

Cycle 4:
  PE[1,1]: accumulates from above (PE[0,1]) and left (PE[1,0])
  Final result: C = [[c11, c12], [c21, c22]]
  where c11 = a11*b11 + a12*b21, c12 = a11*b12 + a12*b22
        c21 = a21*b11 + a22*b21, c22 = a21*b12 + a22*b22
```

**2c) When each outperforms the other:**

MXU excels when: computations are dense, regular, and the entire graph can be compiled ahead of time (Google's production workloads). The tight integration with XLA enables aggressive fusion that minimizes memory traffic.

Tensor Cores excel when: workloads require dynamic control flow, irregular operations, or when using frameworks that don't compile through XLA (e.g., native PyTorch). The CUDA ecosystem provides more tools for custom operations.

---

### Answer 3: OCS Advantages

**3a) Physical mechanism:**

OCS uses MEMS (Micro-Electro-Mechanical Systems) mirror arrays. Each input fiber's light beam hits a tiny mirror that can be physically tilted to reflect the light toward a specific output fiber. When the topology needs to change, the mirror angles are adjusted (taking ~10 microseconds). The light signal carries the same data as electrical signals but passes through the switch without any electrical processing -- hence the switch is transparent to the protocol.

**3b) Advantages over fixed electrical interconnects:**

1. **Multi-tenant isolation**: Different tenants' traffic travels through physically separate optical paths. One tenant's heavy gradient communication cannot cause congestion for another tenant, as would happen in a shared electrical network.

2. **Fault tolerance**: If a chip or link fails, OCS can re-route around the failure within microseconds. In a fixed 2D Torus, a single chip failure breaks the continuity of the ring and requires complex software-level workarounds.

3. **Resource allocation flexibility**: Before OCS, a physical TPU Pod (e.g., 256 chips) had to be allocated as a whole to a single job. Any leftover chips were unusable by other jobs. With OCS, the 4096-chip v4 Pod can be dynamically partitioned into sub-clusters of any size (e.g., 1024 + 1024 + 2048) with no fragmentation.

4. **Power efficiency**: Optical switches consume power proportional to the number of ports (not bandwidth). Electrical switches consume power proportional to bandwidth, so at high data rates, optical becomes more efficient.

**3c) Impact on job scheduling:**

OCS virtually eliminates fragmentation. Consider a 4096-chip Pod: if a job needs 1000 chips, the scheduler can allocate exactly 1000 chips and reconfigure the OCS to form a contiguous 2D Torus from those chips. The remaining 3096 chips are fully intact for other jobs. This dramatically improves utilization.

For mixed workloads: large training jobs + small inference jobs can coexist on the same physical infrastructure, with OCS providing hard performance isolation.

**3d) Limitations:**

OCS switching latency (~10 us) is much higher than electrical switching (nanoseconds). This makes OCS unsuitable for per-message or per-batch routing. OCS is best for circuit-switched topologies that change infrequently (job-level scheduling). For workloads requiring dynamic routing at millisecond granularity, a hybrid approach (OCS + electrical packet switching) may be preferred.

---

### Answer 4: TPU vs GPU Tradeoffs

| Scenario | Better choice? | Reasoning |
|----------|---------------|-----------|
| Large-batch dense Transformer (100B params) on 1024 chips | TPU v4/v5p | TPU's 2D Torus + OCS provides near-linear scaling efficiency for all-reduce at scale. TPU's MXU excels at the dense matrix multiplications in Transformer layers. |
| Low-latency inference of BERT-Large (batch size=1) | GPU (e.g., NVIDIA T4/L4) | TPU is designed for high throughput on large batches. For batch=1 inference, the overhead of TPU's compilation and memory hierarchy adds latency. GPU + TensorRT achieves sub-ms latency. |
| Training a recommendation model with 100B embedding table | TPU v4 | SparseCore on TPU v4 is purpose-built for embedding lookups -- this is TPU's unique advantage. GPU has no equivalent hardware, making embedding the bottleneck. |
| Small-batch training of 1B-parameter CNN | GPU | TPU's compilation overhead is amortized over large batches. For small-batch rapid prototyping, GPU's eager execution and rich debugging tools are more productive. |
| Sparse MoE model with 1T total parameters | TPU v4/v5p | TPU's high-bandwidth interconnect (OCS) enables efficient all-to-all communication needed for MoE routing. GPU clusters often bottleneck on inter-node bandwidth for MoE. |
| Edge inference (<50W power budget) | GPU (Jetson series) | TPUs are datacenter-scale hardware, not available for edge deployment. NVIDIA Jetson and other edge SoCs are designed for this power envelope. |
| Scientific computing (FP64 matrix ops) | GPU (NVIDIA H100/A100) | TPUs are optimized for ML numeric formats (BF16, INT8). FP64 performance on TPU is limited, while NVIDIA GPUs have dedicated FP64 Tensor Cores. |
| Multi-modal model training | TPU (if Google-internal) or GPU | TPU's advantage depends on the specific architecture of the multi-modal model. If it's a Transformer-based model, TPU excels. If it involves custom ops, GPU's flexibility is better. |

---

### Answer 5: XLA Compiler Optimization

**5a) Compilation stages:**

| Stage | Input | Output | Key transformations |
|-------|-------|--------|-------------------|
| HLO Building | High-level IR from TF/JAX (graph of ops) | HLO (High Level Optimizer) IR | Lower framework ops to XLA's HLO ops. Each op becomes an HLO instruction. |
| HLO Optimization | HLO IR (unoptimized) | HLO IR (optimized) | Algebraic simplifications, constant folding, dead-code elimination, **operator fusion**, layout assignment, memory analysis. |
| Parallelization (SPMD Partitioner) | Optimized HLO | Partitioned HLO | Replicates computation across devices, inserts all-reduce/collective ops for gradient synchronization, partitions tensors according to sharding annotations. |
| Code Generation | Partitioned HLO | TPU executable (low-level microcode) | Lowers HLO ops to TPU-specific instructions. Assigns operations to MXU, VPU, SPU. Schedules instruction pipeline. Manages HBM-to-UB data movement. |

**5b) Operator Fusion Example:**

**Without fusion:**
1. Concatenate kernel: reads x, y from HBM, writes h to HBM.
2. Dot-product kernel: reads W, h from HBM, writes z to HBM.
3. Reduce-sum kernel: reads z from HBM, writes out to HBM.

**Total: 3 kernel launches, 5 HBM read/writes.**

**With fusion:**
XLA's fusion pass groups (concatenate -> dot -> reduce-sum) into a single fusion region. The fused kernel:
1. Reads x, y, W directly from HBM into the Unified Buffer (UB).
2. Performs concatenation in-register (no HBM write).
3. Performs the dot product using the MXU (streaming from UB).
4. Performs the reduce-sum in the VPU (vector unit).
5. Writes the final output once to HBM.

**Total: 1 kernel launch, 4 HBM reads + 1 HBM write.**

**5c) Importance of fusion for TPU:**

TPU's memory hierarchy is the key reason fusion matters more than on GPU:
- TPU has a limited Unified Buffer (~28 MB on v4, compared to GPU's multi-MB L2 cache).
- Every HBM read/write costs significantly more energy and latency than a UB access.
- TPU does **not** have the sophisticated multi-level cache hierarchy that GPUs have (L1, L2, L3).
- Therefore, the cost of writing intermediate results to HBM and reading them back is extremely high.
- Fusion allows the compiler to keep intermediate values in the UB or pass them directly between MXU and VPU without touching HBM.
- For GPU, the L1/L2 caches can sometimes absorb intermediate traffic -- but TPU requires explicit data movement management, making fusion essential for any acceptable performance.

Without fusion, a TPU program is often memory-bandwidth-bound; with fusion, it becomes compute-bound on the MXU, achieving 80%+ hardware utilization.

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
