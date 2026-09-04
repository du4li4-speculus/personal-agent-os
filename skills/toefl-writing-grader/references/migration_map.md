# TOEFL Writing 迁移记录

## 来源与优先级

本次迁移使用桌面版 `toefl-writing-grader/SKILL.md` 作为当前 canonical 领域规则，使用其 handoff、ADR 和脚本说明做 provenance 追溯；外部“学生写作和批改”目录中的编号 826–831 及现有学生/家长成品只用于回归验收，不作为学生数据或新评分规则。

优先级固定为：

1. 当前 `skills/toefl-writing-grader/SKILL.md`；
2. 当前输入/证据/assessment schema 与本 Skill 的验证契约；
3. canonical source 中的机械脚本行为说明；
4. `references/` 中的历史 ADR/legacy 解释；
5. 826–831 产品样例的可观察布局和字段要求。

历史资料不能覆盖当前六维规则。尤其是旧的邮件五维、旧权重或旧总分阶梯，只保留作变更背景；迁移没有把它们重新启用。

## 组件映射

| 原有逻辑 | 迁移位置 | 处理 |
| --- | --- | --- |
| 多格式/Pages 提取 | `input_adapters/`、`input/` | 新增统一输入边界，保留缺口 |
| 原文、题目、造句批注证据 | `extractor/`、`evidence/` | 新增 evidence id 和 provenance |
| 当前 Email/Academic 六维 rubric | `SKILL.md`、`assessment/` | 保持现行口径，不重权重 |
| 诊断 ability layers | `diagnosis/`、`schemas/diagnostic.schema.json` | 保留 task/organization/language/reasoning |
| 学习闭环与练习生成 | `learning/`、`templates/practice_generator.md` | 保留诊断→练习→重写→复评 |
| 学生/家长/教师产物 | `artifacts/`、现有 templates/schema | 共享单一 assessment 数据 |
| 教师覆盖与验证 | `schemas/teacher_override.schema.json`、`schemas/validation_record.schema.json` | 覆盖可追踪，不自动改规则 |

Agent OS runtime 不在本次修改范围内；manifest 只声明本 Skill 的输入/输出，不改变 runtime 状态机。
