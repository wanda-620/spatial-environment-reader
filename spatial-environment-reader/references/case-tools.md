# 案例工具

批量材料或复杂项目才需要这些脚本；少量图片可以直接按 `SKILL.md` 分析。

## 建立案例底稿

```bash
python3 scripts/create_case.py /path/to/sources /path/to/case
```

输出：

- `source_manifest.json`：支持文件的相对路径、大小、SHA-256、图像像素、PDF 页数或 PPTX 幻灯片数（能可靠取得时）；
- `evidence.jsonl`：空白证据记录；
- `spatial-report.md`：报告底稿。

脚本拒绝写入已存在的输出目录，避免覆盖人工分析。需要重建时，请使用新的案例目录；不要让自动化脚本删除已有证据或报告。

脚本只做清单和底稿，不执行 OCR、页面渲染或空间判断。`page_or_slide_count: null` 表示当前运行环境无法可靠读取，不表示文件为空。

## 校验证据

```bash
python3 scripts/validate_case.py /path/to/case
```

校验重复编号、必填字段、来源文件、枚举值、数值单位和推断依赖。错误导致非零退出；警告表示证据链仍可改进。脚本不会替代视觉核验。
