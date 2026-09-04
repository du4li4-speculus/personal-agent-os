# 证据层

`extractor/evidence_extractor.py` 将 `source_bundle.json` 转为 `evidence.json`。输出只描述“从哪里提取到了什么”和“还缺什么”，不产生分数、不决定题型，也不替学生补写文本。

## 证据类型

- `prompt_text`：仅来自明确标记为 `role=prompt` 的题目文字。
- `response_text`：仅来自明确标记为 `role=response` 的学生文字。
- `annotation`：例如 Pages 中可直接检出的「造句：错 x/10」证据，并保留原始短语。
- `image_reference`：图片或 Pages 内嵌图片的 provenance；需要 OCR/视觉转录后才有文本证据。
- `unclassified_text`：存在文本但来源角色未明确，不可直接当成题目或学生答案。

## assessment 前必须检查

`summary.assessment_ready` 只有在题目和正文均有明确证据且没有未处理 gap 时才为真。以下情况必须停止评分或请求补充来源：

- 没有明确题目来源；
- 图片仍处于 `pending_ocr`；
- PDF/DOC 只有图像层且未转录；
- 原文真实断尾或文件解析失败；
- 题目与正文无法按 evidence id 交叉核验。

每条评语、任务点判断和语法/搭配记录都应回链至少一个 `evidence_id`。证据层不允许引用其他学生或历史同题文本。

## 实现入口

```bash
python extractor/evidence_extractor.py source_bundle.json -o evidence.json
```

契约见 `schemas/evidence.schema.json`。即使 `AnnotationAuthorStorage` 为空，也要保留 `absence_is_not_proof: true` 的事实记录。
