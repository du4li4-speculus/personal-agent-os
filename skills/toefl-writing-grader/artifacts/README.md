# 产物层

学生版、家长版和教师 dashboard 使用同一份 assessment、quant inputs、能力光谱和 evidence 回链。产物层只负责读者呈现，不产生第二套评分。

## 学生版

- 首页：三分数卡 → 邮件/学术六维雷达 → 量化雷达/学术能力光谱。
- 后续页：当前提交题型逐篇原文（只呈现一次）和六维详细点评；每条判断能回链 evidence。
- 可见标签使用中文读者标签，不出现 CEFR、内部代码、规则来源或假设性错误示例。

## 家长版

- 严格一页：三分数卡、两类写作雷达、量化雷达、能力光谱、1 个最大优点、2 个待提升方面、2 条对应动作。
- 不放学生原句示例、不静默裁切；一页放不下即验证失败。
- 历史趋势只有在存在同一学生可比正式记录时才显示，不能由单次样本推断稳定性。

## 教师 dashboard

至少呈现学生状态、diagnostic、learning loop、practice tasks、validation record 和 override history。教师 override 必须可追踪、可撤回，不得直接修改当前评分规则。

现有产物契约保留在 `schemas/artifact.schema.json`，现有 dashboard 模板保留在 `templates/teacher_dashboard.md`。
