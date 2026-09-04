# 输入层

输入层负责把本次用户提供的内容变成统一的 `source_bundle.json`。它不评分、不猜学生姓名、不补全断尾，也不把历史文件自动合并进当前作业。

## 支持的来源

| 来源 | 适配器 | 处理方式 | 未完成时的标记 |
| --- | --- | --- | --- |
| 纯文本 / Markdown | `input_adapters/text_adapter.py` | 保留原文与编码 | `complete` |
| PDF / DOCX | `text_adapter.py` | 优先文本层；无文本层时保留缺口 | `pending` / `partial` |
| DOC | `text_adapter.py` | 记录文件身份，不伪造转换结果 | `pending` |
| PNG / JPG 等截图 | `input_adapters/image_adapter.py` | 保存图像 provenance，等待 OCR/视觉转录 | `pending_ocr` |
| Apple Pages | `input_adapters/pages_adapter.py` | 检查 `Index/Document.iwa` 开头和全文可见文本，登记 `Data/` 图片与批注存储 | `complete` / `partial` |

每个 source 必须带 `source_id`、顺序、角色、文件摘要、原始格式、提取方法和警告。角色只有在用户或上游明确提供时才使用 `prompt`、`response` 或 `annotation`；否则保持 `unknown`。

## 输入门禁

1. 先定位本次文件，再读取内容；不从历史目录补写当前正文。
2. 题目截图/文字和学生正文是独立来源，不能把一个来源推断成另一个来源。
3. `.pages` 中 `AnnotationAuthorStorage` 缺失或为空，只能记录“未发现可读批注存储”，不能下结论说没有批注。
4. 原文真实断尾、解析失败、OCR 待处理均写入 `extraction.warnings` 或后续 evidence gap。
5. 适配完成后只交付 `source_bundle.json`，assessment 必须继续经过证据层。

## 实现入口

```python
from input_adapters import normalize_sources

bundle = normalize_sources(
    ["prompt.txt", "student.txt"],
    roles=["prompt", "response"],
    output_path="source_bundle.json",
)
```

JSON 结构见 `schemas/source_bundle.schema.json`。`input_adapters/` 是机械适配器；本文件和 `SKILL.md` 是事实边界，不在适配阶段引入评分规则。
