# 评测和计分

在仓库最外层选择数据集，包装器会调用对应的评测器：

```bash
python3 -m arex_v2 list
python3 evaluate.py BrowseComp --n 1 --dry-run
python3 evaluate.py BrowseComp --n 10 --save-path runs/browsecomp-10
```

`--start-index I --n N` 表示评测行号区间 `[I, I+N)`。每个数据集会在结果根目录
下拥有独立目录。真实运行前包装器会检查数据路径；dry-run 只打印最终子进程命令。

## Research 数据集

每题都会写出 `result.json`。汇总 `score_result.score` 前，先检查 `status`、
`official_scorer`、`judge_raw` 和错误字段。缺少数据或凭据属于配置错误，不应
统计为模型答错。

| 数据集 | 输入和计分 |
| --- | --- |
| BrowseComp | 加密 CSV；BrowseComp 官方 judge |
| DeepSearch-QA | CSV；官方 Gemini-autorater 风格 scorer |
| HLE | 纯文本 HLE JSONL；0724 HLE judge，另有 `metrics.full_credit` |
| GAIA-2023-validation-text-103 | 纯文本 GAIA JSONL；WebAgent 风格 text judge |
| xBench-DeepSearch-2510 | 加密 CSV；xBench 官方 judge |
| HLE-NoTool | HLE parquet；HLE judge |
| WideSearch-en / WideSearch-zh-en-prompt | WideSearch JSONL；官方表格分数 |
| WideSearch-en-sft-eval / WideSearch-zh-sft-eval | 同一表格评分在 SFT split 上的结果 |
| DeepWideSearch | DeepWideSearch JSONL；官方表格评分 |
| MoNaCo | execution traces；Monaco 分数 |
| DeepResearch-Bench | query 和 criteria 文件；RACE 分数 |
| BrowseComp-Zh-official-en-prompt | BrowseComp-ZH judge |

仓库为下面四个数据集提供下载流程：

```bash
python3 -m arex_v2 download BrowseComp
python3 -m arex_v2 download DeepSearch-QA
python3 -m arex_v2 download HLE                 # 需要 HF_TOKEN 和访问权限
python3 -m arex_v2 download GAIA-2023-validation-text-103  # 需要 HF_TOKEN
python3 -m arex_v2 download --list
```

其他数据集仍然可以从同一个入口评测，但需要按照上游许可准备文件并放到配置的
路径。单数据集运行可以用 `--data-path`，也可以先用 `download --list` 查看路径。

## Frontier-CS 算法题

下载公开题库并评测 C++17 解答：

```bash
python3 scripts/download_data.py --dataset algorithmic
python3 -m arex_v2 algorithmic 1 path/to/solution.cpp --backend docker
```

checker 会返回 `scoreRatio`、`scoreRatioUnbounded` 等 case 分数。请保留完整
checker 和 Docker 日志；只有所有必要 case 都通过才算通过。

## MLE-bench Lite

准备并运行一场比赛，然后用 host grader 评分：

```bash
MLE_BENCH=$HOME/mle-bench python3 -m arex_v2 mle leaf-classification --prepare
MLE_BENCH=$HOME/mle-bench python3 -m arex_v2 mle leaf-classification
MLE_BENCH=$HOME/mle-bench \
  bash vendor/mle_lite/scripts/grade.sh runs/<run-dir> leaf-classification
```

最终指标看 `grade.log` 里的 `score`、`valid_submission` 和 medal/threshold 字段。
容器内 `/validate` 输出只用于诊断。

## 可复现记录

在每个结果根目录旁记录 Git commit、model、base URL、任务范围、mode、评测器 extras
和数据 checksum，绝不要记录 API key 的值。上游版本和许可见 `SNAPSHOT.txt`、
`THIRD_PARTY_NOTICES.md`。
