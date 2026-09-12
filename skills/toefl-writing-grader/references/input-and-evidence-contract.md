# Input and Evidence Contract

Load this reference for input normalization, attachment parsing, prompt verification, provenance, and assessment-readiness work.

### 1. 事实源与题目核验

- 批改文本只能来自用户本次提供的文件。先适配、提取并保存证据，再评分；正文真实断尾原样保留，禁止用记忆、旧稿、其他学生文本或语义推测补写。
- 学生姓名一律以本次文件与落款为准；禁止依据历史档案或猜测自行推断、替换姓名。交付前复查构建配置、PDF 文件名、PDF 首页、归档目录和记忆记录五处姓名是否一致。
- 批改过程记录和回复中不得写“与某批次/学生同题”；题目直接描述本次内容，不做跨学生同题对照。
- 批改前读取本次题目截图或题目文字，并与正文提取结果交叉核验；题目缺失时如实记录缺失，不得假称已核验。
- `.pages` 必须检查 `Index/Document.iwa` 的第一行/开头及全文中文字段，确认是否存在造句批注（如「造句：错 x/10」）；`AnnotationAuthorStorage` 为空不代表没有批注。
- 邮件按题目逐行拆任务。一行出现 `and` 时拆成多个子问题，逐项核对回答与扩展。
- 学术讨论检查从题目要求起点推进到终点的议论与事例逻辑链，只有观点句不算完整扣题。
- 学术扣题以题目最后 1–2 句问句中的核心概念为锚；`such as` 后的例子不要求逐条覆盖。只有问句含 `which approach` / `which way` 等比较词时，才回到题干选项；存在多个选项时，完整覆盖任意一方即可视为切题干净，不要求两方都写。
- 没有教师修订或批注时，按当前 rubric 自评，并把分数、弱点和证据显式录入；不得假装文件含有批注。

## Runtime boundary

- `source_bundle.json` is the single input fact source.
- `evidence.json` is the traceable source used before assessment.
- Assessment must not bypass the evidence layer to read attachments directly.
- Apply format-specific inspection only when that format is present. For example, inspect `.pages` internals only for a `.pages` input.
- Check identity consistency only across artifacts emitted or updated in the current run.
