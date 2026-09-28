# 评测和计分

使用数据集名称和 `--n` 选择任务。包装器会把
`--start-index I --n N` 转换为评测器区间 `[I, I+N)`。

## Research 数据集

每题都会写出 `result.json`。只有在检查 `status`、`official_scorer`、
`judge_raw` 以及 `error_type`、截断字段后，才汇总 `score_result.score`。

| 数据集 | 输入 | 计分信号 |
| --- | --- | --- |
| BrowseComp | 加密 `browse_comp_test_set.csv` | BrowseComp 官方 judge；逐题看 `score_result.score`，汇总正确率 |
| HLE | `text_items.jsonl` 和附件 | 0724 HLE judge；`score_result.metrics.full_credit` 表示满分 |
| GAIA-2023-validation-text-103 | 文本 JSONL 和引用的附件 | WebAgent 风格 LLM judge；平均逐题分数，并记录 leak filter 结果 |
| DeepSearch-QA | `DSQA-full.csv` | 官方 Gemini autorater 风格 scorer；解析失败单独统计 |

评测器固定工具协议：`search` 和 `google_scholar` 调用 Serper，`visit` 调用
Jina Reader。缺少凭据属于配置错误，不应统计为模型错题。

注册表还提供以下数据集。它们都使用逐题 `result.json`；上游 scorer 名称会
记录在 `official_scorer`，数值结果在 `score_result` 中。

| 数据集 | 计分信号 |
| --- | --- |
| xBench-DeepSearch-2510 | xBench 官方 grader 分数 |
| HLE-NoTool | HLE judge 分数和 `metrics.full_credit` |
| WideSearch-en / WideSearch-zh-en-prompt | WideSearch 官方表格分数 |
| WideSearch-en-sft-eval / WideSearch-zh-sft-eval | SFT split 的同类 WideSearch 分数 |
| DeepWideSearch | DeepWideSearch 官方表格分数 |
| MoNaCo | Monaco execution-trace 分数 |
| DeepResearch-Bench | DeepResearch-Bench RACE 分数 |
| BrowseComp-Zh-official-en-prompt | BrowseComp-ZH judge 分数 |

先做 smoke test：

```bash
python3 -m arex_v2 research BrowseComp --n 1 --dry-run
python3 -m arex_v2 research BrowseComp --n 1 --save-path runs/browsecomp-smoke
```

## Frontier-CS 算法题

```bash
python3 scripts/download_data.py --dataset algorithmic
python3 -m arex_v2 algorithmic 1 path/to/solution.cpp --backend docker
```

judge 会编译 C++17 程序、运行隐藏测试，并返回 `scoreRatio`、
`scoreRatioUnbounded` 等 checker case 分数。只有所有必要 case 都通过才算
通过；完整保留 Frontier/Docker 日志。

## MLE-bench Lite

一次准备和运行一个比赛：

```bash
MLE_BENCH=$HOME/mle-bench python3 -m arex_v2 mle leaf-classification --prepare
MLE_BENCH=$HOME/mle-bench python3 -m arex_v2 mle leaf-classification
```

用 host grader 评测生成的 submission：

```bash
MLE_BENCH=$HOME/mle-bench \
  bash vendor/mle_lite/scripts/grade.sh runs/<run-dir> leaf-classification
```

最终指标看 `grade.log` 中的 `score`、`valid_submission` 和 medal/threshold
状态。容器内 `/validate` 只是诊断信息。

## 可复现记录

在每个结果目录旁记录 Git commit、model name、base URL、任务范围、mode、
评测器 extras 和数据 checksum，绝不要记录 API key 的值。上游 commit 和许可
信息保存在 `SNAPSHOT.txt`、`THIRD_PARTY_NOTICES.md`。
