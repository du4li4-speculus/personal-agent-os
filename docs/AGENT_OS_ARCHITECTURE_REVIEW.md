# Personal Agent OS 架构审查总结

日期：2026-09-04
目标：将当前仓库升级为边界清晰、可发现、可执行、可验证的 Agent OS。

## 结论

当前仓库已经具备“控制平面 + 领域 Skill”的基本形态：`core` 定义原则，`registry` 负责 Skill 索引，`runtime` 管理执行生命周期，`skills` 承载领域能力。

但目前的边界主要由目录和说明文档表达，尚未通过统一契约和 Runtime 强制执行。最关键的缺口是：Runtime 仍依赖调用方传入 `executor`，Registry 不能直接解析并调用 Skill；TOEFL Skill 也尚未形成从输入到最终产物的完整可执行链。

## 审查基线

- GitHub 当前 `main`：`3176353`
- 本地 checkout：`ce80768`
- 本地分支包含 2 个尚未推送到本地 `origin/main` 的 Runtime 提交
- 本地工作树还包含未提交的 TOEFL Skill 扩展、schema、适配器和试运行产物
- 现有 Runtime 测试结果：15/15 通过

GitHub 当前 `main` 与本地工作树不是同一状态：远端包含 `cognition/`、架构边界和 Registry 政策；本地包含可执行 Runtime 和更完整的 TOEFL Skill 工作，但尚未合并远端的新架构文档。

## 1. 当前目录结构分析

### 控制平面

- `core/`
  - `agent.md`：全局执行原则
  - `workflow.md`：Runtime 生命周期及门禁契约
- `cognition/`：扩展、批判、决策、记忆协议；当前存在于 GitHub `main`，本地 checkout 尚未同步
- `registry/`
  - `skill_registry.yaml`：Skill 名称、版本、类型、状态和路径
- `runtime/`
  - Registry 与 Skill 加载
  - 状态机控制
  - 执行日志与执行证明
  - Artifact 路径和存在性校验
  - Trace 验证
  - Runner 与 CLI
- `tests/`
  - 当前主要覆盖 Runtime 的成功、失败、恢复和安全路径

### 能力平面

- `skills/toefl-writing-grader/`
  - `SKILL.md`：当前 TOEFL 写作领域规则
  - `manifest.yaml`：输入、输出和 Runtime 依赖声明
  - `input_adapters/`：文本、图片、文档和 Pages 输入适配
  - `extractor/`：从 `source_bundle.json` 提取 `evidence.json`
  - `assessment/`、`diagnosis/`、`learning/`、`artifacts/`、`validation/`：阶段边界说明
  - `schemas/`：领域数据契约
  - `templates/`：练习和教师 Dashboard 模板
  - `output/`：当前混入 Skill 源码目录的实例运行产物

### 文档平面

- `docs/superpowers/specs/`：Runtime 设计说明
- `docs/superpowers/plans/`：Runtime 实施和 TOEFL 迁移计划
- GitHub `main` 中另有 `ARCHITECTURE_BOUNDARIES.md` 和 `REGISTRY_POLICY.md`

## 2. 已有组件职责分析

| 组件 | 当前职责 | 成熟度判断 |
| --- | --- | --- |
| Core | 定义证据优先、Skill 优先、验证后交付等全局原则 | 原则清晰，但不可执行 |
| Cognition | 定义探索、批判、决策和记忆方法 | 文档骨架，尚未接入生命周期 |
| Registry | 提供 Skill 静态索引 | 能发现目录，不能发现执行入口 |
| Registry Loader | 校验 Registry 结构和 Skill 路径安全 | 基础能力完整 |
| Skill Loader | 加载 Skill 定义和 manifest，校验名称、版本、类型 | 未处理 inputs、intermediate outputs、entrypoint 和 validators |
| State Manager | 执行合法状态转换及一次恢复 | 基础生命周期完整 |
| Runner | 编排 Skill 加载、执行、Artifact 门禁和 Trace | 当前最成熟的控制平面组件 |
| Artifact Manager | 校验声明输出是否存在、非空且不越界 | 只验证文件，不验证内容和领域语义 |
| Validator Engine | 验证通用 Trace 和 Artifact 引用 | 未执行领域 JSON Schema 或成品质量验证 |
| TOEFL Input/Evidence | 统一输入并保留 provenance，生成证据 | 已有部分可执行代码 |
| TOEFL Assessment 之后的阶段 | 评分、诊断、学习闭环、报告和领域验证 | 目前主要是规则、schema 和模板，缺少完整执行器 |

## 3. 与目标架构的差距

### P0：Runtime 不能自主调用 Skill

当前 Runner 要求外部调用方传入 `executor`。因此调用方必须预先知道 Skill 的实现，Registry 还不是“可调用能力注册中心”。

目标应为：

`Task -> Registry -> Skill Entry Point -> Runtime Gates -> Artifacts -> Validation`

### P0：TOEFL Skill 尚未形成完整执行闭环

当前已有输入适配和证据提取，但缺少或尚未接入：

- assessment executor
- diagnosis executor
- learning-loop executor
- artifact renderer
- domain validator
- 可由 manifest 解析的 Skill entrypoint

### P1：中间阶段没有进入 Runtime 控制

TOEFL Skill 使用 `source_bundle.json` 和 `evidence.json` 等中间产物，但 Runtime 只把 Skill 视为单次黑盒执行，并且忽略 manifest 中的 `intermediate_outputs`。

### P1：输入契约不一致

Runtime 只接受一个可选 `input_path`；TOEFL Skill 实际需要多个输入、输入角色以及混合文件格式。两者需要统一为明确的多源输入契约。

### P1：依赖和能力声明不足

实际执行可能依赖 `pdftotext`、Pages/IWA、Snappy、OCR 或视觉转录，但 manifest 只声明两个通用 Runtime capability，Runtime 无法在执行前准确判断环境是否可用。

### P1：Project、Memory 和 Run Data 边界缺失

架构文档声明了 Project Layer 和 Memory Layer，但仓库没有对应的接口或存储契约。真实学生输出目前位于 Skill 目录内，混淆了源码、运行数据、隐私数据和可提交内容。

### P2：边界没有自动化执行

仍缺少：

- Registry schema
- Manifest schema
- Skill entrypoint 校验
- 跨层依赖或 import 规则
- 领域 schema 自动验证
- 输入到交付的端到端测试
- 运行产物与隐私数据隔离策略

## 4. 潜在冲突点

1. GitHub 当前 `main`、本地 Runtime 提交和本地未提交 TOEFL 工作形成三套状态，直接修改容易覆盖有效成果。
2. GitHub Registry 声明 TOEFL Skill 为 `1.0.0`，manifest 为 `2.0.0`；本地 Runtime 会拒绝该版本漂移。
3. GitHub 的状态机引用 `RECOVERY`，远端契约尚未完整定义该状态；本地实现已补齐。
4. `core` 和 `cognition` 都包含思考与决策规则，需要明确唯一权威和依赖方向。
5. 旧迁移计划要求 Runtime 保持不变，与本次 Agent OS 升级目标存在冲突；旧计划应作为历史记录，而非当前最高优先级约束。
6. Runtime 把 Skill 视为单个 executor，TOEFL Skill 则表达多阶段流水线，需要决定采用复合 Skill 还是多个可组合 Skill。
7. manifest 声明的最终输出名与当前试运行产物的目录和文件名不完全一致，现有 Artifact Gate 无法直接接受该输出。
8. `SKILL.md`、schema、README 和模板都在描述领域规则，但尚未明确机器执行时的唯一事实源。

## 5. 实施顺序建议

### 阶段 0：对齐仓库状态

- 对比 GitHub 当前 `main`、本地两个 Runtime 提交和未提交 TOEFL 工作
- 形成保留、合并、重构和历史归档清单
- 保留全部现有用户修改和运行产物，不直接覆盖或删除

### 阶段 1：建立唯一架构契约

明确以下边界和依赖方向：

- `core`：全局不变量和治理规则
- `cognition`：可复用思考协议
- `registry`：能力发现及版本解析
- `runtime`：通用编排、门禁、Trace 和恢复
- `skills`：领域执行逻辑与领域验证
- `projects`：项目配置和目标
- `memory`：可复用经验与作用域
- `runs`：输入、中间数据、Trace 和最终产物

### 阶段 2：升级机器可读契约

- 为 Registry 和 manifest 建立 schema
- 增加 `entrypoint`、inputs、intermediate outputs、capabilities、validators 和版本策略
- 明确 Skill 是单体复合能力还是可组合阶段集合

### 阶段 3：升级 Runtime

- 根据 Registry 自动解析和加载 Skill entrypoint
- 支持多源输入和明确角色
- 对中间产物执行阶段级门禁
- 记录阶段级 Trace 和 provenance
- 通过可插拔 validator 执行领域验证
- 保持 Runtime 不包含 TOEFL 领域规则

### 阶段 4：完成 TOEFL Skill 执行链

接通完整流程：

`input -> evidence -> assessment -> diagnosis -> learning -> artifacts -> validation`

所有领域规则、schema 和成品质量检查留在 Skill 内部。

### 阶段 5：隔离数据和输出

- 将实例输入、运行 Trace 和报告移出 Skill 源码目录
- 使用按 project/run id 组织的运行目录
- 建立隐私、归档和 Git 提交策略

### 阶段 6：补齐验证体系

- Runtime contract tests
- Skill contract tests
- 跨层边界测试
- 领域 schema 测试
- 真实流水线端到端 fixture
- 失败、恢复和不可交付路径测试
- CI 和架构文档校验

## 推荐执行原则

后续应以本地当前工作树作为待整理实现，以 GitHub 当前 `main` 作为远端架构基线。先完成三方状态对齐和契约定版，再修改 Runtime 与 TOEFL Skill，避免在边界尚未确定前扩大实现分歧。
