# AREX-2 评测套件

AREX-2 是 `self_evolving_v15` 使用的评测仓库，统一放置 research、Frontier-CS 算法题和 MLE-bench Lite 三条评测线。数据集、模型输出和密钥不进 Git，仓库只保留评测器、数据集协议和可复现命令。

[English](README.md) · [逐数据集评测说明](data/README.md) · [实验与复现](scripts/README.md) · [项目主页](https://545999961.github.io/ax2/)

## 目录

```text
evaluation/   CLI、评测适配器和固定版本的评测器
data/         数据集配置、准备清单和逐数据集说明
assets/       benchmark PDF/SVG、logo 和项目主页
scripts/      下载脚本、运行配置、算法题实验和测试
evaluate.py   选择 research 数据集的根目录快捷入口
```

每个数据集的 `config.json`、`prompt.py`、`judge_local.py` 和 `judge_offical.py` 都在 `data/` 下，评测输入、评分器、指标和运行命令见 [data/README.md](data/README.md)。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[research]'   # research
# pip install -e '.[frontier]' # Frontier-CS
# pip install -e '.[all]'      # 全部依赖
python3 -m arex_v2 doctor
```

## Research 评测

```bash
python3 -m arex_v2 list
python3 evaluate.py BrowseComp --n 1 --dry-run
python3 evaluate.py BrowseComp --n 10 --save-path runs/browsecomp-10
python3 evaluate.py HLE --start-index 100 --n 20
```

外层只需要选择数据集，程序会自动找到对应配置、数据路径、prompt、loader 和 scorer。默认数据目录是 `data/files/`，也可以使用 `--data-root` 或单数据集的 `--data-path`。

有下载配方的数据集：

```bash
python3 -m arex_v2 download BrowseComp
python3 -m arex_v2 download DeepSearch-QA
python3 -m arex_v2 download HLE                 # 需要 HF_TOKEN 和访问权限
python3 -m arex_v2 download GAIA-2023-validation-text-103  # 需要 HF_TOKEN
python3 -m arex_v2 download --list
```

## Frontier-CS 算法题

评测器源码在 `evaluation/algorithmic/`，题目和运行结果在 `data/algorithmic/`：

```bash
python3 -m arex_v2 download algorithmic
python3 -m arex_v2 algorithmic 1 path/to/solution.cpp --backend docker
```

协议和 `scoreRatio` / `scoreRatioUnbounded` 的含义见 [data/algorithmic/README.md](data/algorithmic/README.md)。

## MLE-bench Lite

```bash
MLE_BENCH=$HOME/mle-bench python3 -m arex_v2 mle leaf-classification --prepare
MLE_BENCH=$HOME/mle-bench python3 -m arex_v2 mle leaf-classification
MLE_BENCH=$HOME/mle-bench \
  bash evaluation/mle_lite/scripts/grade.sh runs/<run-dir> leaf-classification
```

最终分数以 host grader 的 `grade.log` 为准。

## 结果图

![AREX benchmark results](assets/performance/arex-v2-benchmark-results.svg)

原始图表见 [benchmark PDF](assets/performance/arex-v2-benchmark-results.pdf)。

## 检查

```bash
PYTHONPATH=evaluation python3 -m unittest discover -s evaluation/tests -v
python3 -m compileall -q evaluation/arex_v2 evaluation/research_eval/unified_eval scripts
```
