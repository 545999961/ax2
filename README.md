# AREX v2 unified evaluation repository

This repository is the single entry point for the evaluation code used by
`self_evolving_v15`. It keeps the research evaluators, Frontier-CS algorithmic
judge, and MLE-bench Lite harness in one tree while preserving the runtime
contract of each upstream project.

The large Frontier-CS problem archive is excluded from Git. Download it when
an algorithmic task is needed:

```bash
python3 scripts/download_algorithmic.py
```

The downloader writes only `algorithmic/problems/`, validates archive paths,
and accepts `--url` and `--sha256` for a pinned mirror. A clean GitHub clone
therefore stays small and can fetch benchmark data at runtime.

## Layout

```text
arex_v2/                     stdlib-only CLI and subprocess adapters
vendor/frontier_cs/          Frontier-CS Python package snapshot
vendor/harbor_pi_supported/  Harbor runtime source snapshot
algorithmic/                 Frontier-CS judge and scripts; problems on demand
vendor/mle_lite/             MLE-bench Lite pi harness snapshot
vendor/research/             BrowseComp/HLE/GAIA/DeepSearch-QA evaluator
scripts/                     data download and diagnostics helpers
reference/                   original 0919 runner scripts for reproducibility
```

Run `python3 -m arex_v2 list` and `python3 -m arex_v2 doctor` before a real
run. Run artifacts, datasets, model outputs, and credentials are ignored by
Git.

## 凭据与搜索/访问工具

当前仓库不包含任何 API key、token 或私有认证文件；我也清理了提交历史中
的硬编码访问令牌。模型凭据、Kaggle 凭据和网页工具凭据必须由运行环境注入，
不要写进源码、README 或提交记录。

研究任务的工具协议固定为：`search` 使用 Serper，`visit` 使用 Jina Reader。
代码支持两种端点：默认兼容原实验使用的批量代理接口；也可以切到官方端点。
两种模式都只从环境变量读取密钥：

```bash
# Required for the search tool.
export SERPER_API_KEY="$SERPER_API_KEY"
# Required for the batch proxy; optional for a public r.jina.ai endpoint.
export JINA_API_KEY="$JINA_API_KEY"

# Optional: use official providers directly.
export SERPER_API_URL=https://google.serper.dev/search
export SERPER_SCHOLAR_API_URL=https://google.serper.dev/scholar
export JINA_API_URL=https://r.jina.ai
```

官方模式发送 `X-API-KEY` 到 Serper，并以 `https://r.jina.ai/<原始 URL>`
读取页面；代理模式发送代理约定的 JSON，并把同一个环境变量作为请求令牌。
`SERPER_KEY` 和 `JINA_TOKEN` 也作为兼容别名支持。没有设置密钥时，真实
`search`/`visit` 调用会明确报配置错误；`--dry-run` 不会访问网络。

## 统一命令

```bash
python3 -m arex_v2 doctor
python3 -m arex_v2 research BrowseComp --dry-run
python3 -m arex_v2 algorithmic 1 solution.cpp --dry-run
python3 -m arex_v2 mle leaf-classification --dry-run
```

## 每个任务怎么评测

下面的命令会在 `runs/` 或你指定的目录写出逐题结果。最终分数应以每个
任务的 `score_result`、官方 grader 输出和运行日志为准，不要只看模型文本。

### BrowseComp

准备加密的 `browse_comp_test_set.csv`，默认路径是
`vendor/research/datasets/BrowseComp/`，或通过 `--data-path` 指定。运行：

```bash
python3 -m arex_v2 research BrowseComp \
  --model provider/model --data-path /path/browse_comp_test_set.csv \
  --save-path runs/browsecomp
```

每题由 agent 使用 Serper `search`、Serper Scholar 和 Jina `visit`，结束时
生成答案；评测器使用 BrowseComp 官方 judge（含仓库里的 typo patch）。看
`runs/browsecomp/BrowseComp/*/result.json` 中的 `score_result.score`、
`status` 和 `official_scorer`，汇总题目正确率。

### HLE

准备 `text_items.jsonl` 和需要的附件；默认目录是
`vendor/research/hle_0724_vendor/data_json/`。运行：

```bash
python3 -m arex_v2 research HLE --mode direct --model provider/model \
  --data-path /path/text_items.jsonl --save-path runs/hle
```

HLE 使用 0724 HLE harness 和 `HLE_judge.py`。每题由 judge 判断最终答案是否
正确，`score_result.score` 为题级分数，`score_result.metrics.full_credit`
表示是否满分；同时检查 `judge_raw`、`error_type` 和是否发生截断。需要复核
时使用 `--mode refine_summary` 或 README 中 evaluator 支持的 HLE outer 参数，
不要把复核结果和首次结果混在同一目录。

### GAIA-2023-validation-text-103

准备 `standardized_data.jsonl` 以及题目引用的附件目录：

```bash
python3 -m arex_v2 research GAIA-2023-validation-text-103 \
  --data-path /path/standardized_data.jsonl --save-path runs/gaia
```

该配置只评估文本题，并启用 benchmark leak filter。每题由 WebAgent 风格
LLM judge 将模型答案与 `ground_truth` 判为 Correct/Incorrect；汇总
`score_result.score` 的平均值，并记录 judge 原始输出和被拦截的引用。

### DeepSearch-QA

准备 `DSQA-full.csv`：

```bash
python3 -m arex_v2 research DeepSearch-QA \
  --data-path /path/DSQA-full.csv --save-path runs/deepsearchqa
```

评测器按 DeepSearch-QA 官方 Gemini autorater prompt 风格评分。逐题检查
`score_result.status`、`score_result.score`、`official_scorer` 和
`judge_raw`，再计算全体题目的平均分；解析失败要单独统计，不能当作模型错题。

### Frontier-CS algorithmic

算法题是 C++17 程序。先下载题面和测试数据，再交给原 Frontier CLI：

```bash
python3 scripts/download_algorithmic.py
python3 -m arex_v2 algorithmic 1 solution.cpp --backend docker
```

judge 会编译程序、运行隐藏测试并按 checker 返回每个 case 的
`scoreRatio`/`scoreRatioUnbounded`；总分是 case 分数的汇总，全部 case 达到
`1.0` 才是 `passed`。查看 Frontier/Docker 输出中的 `score`、`scoreUnbounded`
和 case 状态。SkyPilot 可把 `--backend docker` 换成 `--backend skypilot`。

### MLE-bench Lite

设置 `MLE_BENCH`，只准备一个比赛可以避免下载完整 22 个比赛：

```bash
MLE_BENCH=$HOME/mle-bench python3 -m arex_v2 mle leaf-classification --prepare
MLE_BENCH=$HOME/mle-bench \
  DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY" \
  python3 -m arex_v2 mle leaf-classification --time-limit 14400
```

一次运行会在 `vendor/mle_lite/runs/<timestamp>_<competition>/` 生成
`submission/submission.csv`、trajectory 和日志。随后用 MLE-bench 官方 grader
评分：

```bash
MLE_BENCH=$HOME/mle-bench \
  bash vendor/mle_lite/scripts/grade.sh runs/<run-dir> leaf-classification
python3 vendor/mle_lite/scripts/summarize.py vendor/mle_lite/runs/
```

最终指标以 `grade.log` 中的 `score`、`valid_submission` 和 medal/threshold
字段为准；容器内的 `/validate` 结果只是运行时诊断，不能替代 host grader。

## 数据与复现

用 `scripts/fetch_dataset.py DATASET URL [--sha256 HASH]` 下载已批准的数据
镜像。仓库不会替用户猜测数据 URL，也不会自动保存访问凭据。发布时请保留
`vendor/` 中的上游许可证和归属文件，并在 release notes 记录上游 commit。
