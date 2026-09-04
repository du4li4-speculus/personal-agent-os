# 学习层

学习闭环承接诊断和 practice generator，不新增评分规则：

`evidence → assessment → diagnosis → targeted practice → timed rewrite → re-extraction → re-assessment`

每个学习动作至少包含：目标能力层、具体任务、时限（如适用）、成功信号和下一次复核所需证据。建议沿用已有域逻辑：

- `task_response`：先把每个 email task point 或 academic 起点—终点写成独立信息块，再补原创细节。
- `organization`：拆清问句/长句，练指代、复现和语义连接，不把连接词数量当作唯一目标。
- `language_control`：围绕严重错误、动词+介词/名词+介词/动宾搭配和高频句型做短练习，再限时重写。
- `reasoning`：用“论点—机制—结果—例证/反驳”的最短完整链复写，不要求为了凑数量改变原立场。

学习动作的成功与否必须由新一轮 evidence 和同一 rubric 验证；一次练习完成不自动改写学生长期状态。结构见 `schemas/learning_loop.schema.json`，练习模板见 `templates/practice_generator.md`。
