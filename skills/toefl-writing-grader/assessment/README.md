# 评估层

本层迁移现有 TOEFL 评分逻辑，不重新设计 rubric。唯一当前规则在 `SKILL.md` 第 3 节；本文件只定义进入评分配置时的稳定映射和同步约束。

## 题型与六维映射

| 题型 | 六维键（稳定配置键） | 读者标签 |
| --- | --- | --- |
| Email | `task_response`, `social_audience_awareness`, `expansion_detail`, `organization_logic`, `grammar`, `vocabulary_sentence` | 切题、社交规范与受众意识、扩展和细节、结构和逻辑、语法、词汇和句型 |
| Academic Discussion | `task_response`, `argument_reasoning`, `grammar`, `organization_logic`, `sentence_function`, `vocabulary_sentence` | 切题、论证与理由、语法、结构和逻辑、句子功能、词汇和句型 |

每篇 piece 独立保存六个 2–5 分和 evidence ids；同题型多篇不得先拼接再评分。雷达图、详细评价、分数卡必须读取同一 piece 记录，禁止手填第二份分数。

## 评估顺序

1. 从 evidence 确认题目任务点、题型和学生正文边界。
2. 邮件逐行拆任务；出现 `and` 时拆成子问题。
3. 学术识别问题类型，检查起点—终点、论证层次、例证和句间连接。
4. 独立评六维；同一问题不在多个维度重复扣分。
5. 记录语法总数、严重错误、搭配错误、扩展细节数、原创关键词和量化输入。
6. 运行同步契约后，才把 assessment 交给诊断和产物层。

## 不变的当前口径

- 语法仍按全篇错误数量定档，并单独列出严重错误与搭配错误。
- 邮件社交维度以礼貌互动、受众角色和结果推理为核心，不把连接词或段落数混入其中。
- 学术论证的“议论 + 例子”在共同支持同一论点时按两条扩展检查，但每个逻辑层仍需有足够展开。
- 学术连接率允许显式连接、指代/复现和 semantic cloud 语义相连三种证据。
- 题目原词不计作原创关键词或高端词；读者产物不得暴露 CEFR 等内部标签。

配置契约见 `schemas/assessment.schema.json`。
