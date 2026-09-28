import argparse
import asyncio
import datetime
import json
import os
import re
import time
import traceback
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from openai import AsyncOpenAI

from unified_eval.loaders import load_samples
from unified_eval.registry import load_dataset_spec
from unified_eval.scorers import score_prediction
from unified_eval.types import DatasetSpec, EvalSample


DEFAULT_DATASET_NAME = "HLE-NoTool"
DEFAULT_RETRY_TOKEN_THRESHOLD = 100000
DEFAULT_RETRY_MAX_ATTEMPTS = 3


def retry_long_enabled(args) -> bool:
    return args.mode == "refine_summary"


def effective_retry_max_attempts(args) -> int:
    if not retry_long_enabled(args):
        return 1
    return max(1, int(args.retry_max_attempts))


def infer_data_format(path: str, default: str) -> str:
    ext = Path(path).suffix.lower()
    if ext == ".parquet":
        return "parquet"
    if ext == ".json":
        return "json"
    if ext == ".jsonl":
        return "jsonl"
    if ext == ".csv":
        return "csv"
    return default


def load_spec(args) -> DatasetSpec:
    spec = load_dataset_spec(args.dataset_name, judge_mode=args.judge_mode)
    data_path = args.dataset_path or args.dataset or args.data_path
    if data_path:
        spec = replace(
            spec,
            data_path=data_path,
            data_format=args.data_format or infer_data_format(data_path, spec.data_format),
        )
    return spec


def has_image_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, float):
        try:
            return not (value != value)
        except Exception:
            return True
    if isinstance(value, str):
        text = value.strip()
        return bool(text) and text.lower() not in ("none", "nan", "null")
    if isinstance(value, dict):
        if isinstance(value.get("bytes"), (bytes, bytearray)):
            return True
        return any(has_image_value(value.get(k)) for k in ("url", "image_url", "path", "image_path"))
    if isinstance(value, (list, tuple)):
        return any(has_image_value(item) for item in value)
    return False


def sample_has_image(sample: EvalSample) -> bool:
    return any(has_image_value(sample.raw.get(key)) for key in ("image", "image_url", "image_path", "images"))


def parse_id_set(text: Optional[str]) -> Optional[Set[str]]:
    if not text:
        return None
    ids = {part.strip() for part in str(text).split(",") if part.strip()}
    return ids or None


def parse_index_set(text: Optional[str]) -> Optional[Set[int]]:
    if not text:
        return None
    values = {int(part.strip()) for part in str(text).split(",") if part.strip()}
    return values or None


def select_samples(
    samples: Sequence[EvalSample],
    args,
) -> List[EvalSample]:
    if not args.include_images:
        samples = [sample for sample in samples if not sample_has_image(sample)]

    target_ids = parse_id_set(args.question_ids)
    if args.question_id:
        target_ids = set(target_ids or set())
        target_ids.add(str(args.question_id).strip())

    target_indices = parse_index_set(args.target_indices)
    if target_ids is not None:
        selected = [sample for sample in samples if str(sample.sample_id) in target_ids]
    elif target_indices is not None:
        selected = [sample for sample in samples if sample.idx in target_indices]
    else:
        end = None if args.end_index is None or args.end_index < 0 else args.end_index
        selected = list(samples[args.start_index:end])

    if args.max_samples is not None:
        selected = selected[: args.max_samples]

    if args.target_shard_count > 1:
        if args.target_shard_rank < 0 or args.target_shard_rank >= args.target_shard_count:
            raise ValueError(
                f"--target-shard-rank must be in [0, {args.target_shard_count}), "
                f"got {args.target_shard_rank}"
            )
        selected = selected[args.target_shard_rank :: args.target_shard_count]

    return selected


def sanitize_tag(value: str) -> str:
    return value.replace("/", "_").replace("\\", "_").replace(":", "_").replace(" ", "_")


def build_output_path(args) -> str:
    if args.output:
        return args.output
    model_tag = sanitize_tag((args.model or "model").split("/")[-1])
    dataset_arg = args.dataset_path or args.dataset or args.data_path or args.dataset_name
    dataset_tag = sanitize_tag(Path(dataset_arg).stem if os.path.exists(str(dataset_arg)) else str(dataset_arg))
    return f"HLE_NoTool_{dataset_tag}_{model_tag}.json"


def load_json_dict(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"prediction output is not a JSON dict: {path}")
    return {str(k): v for k, v in data.items()}


def atomic_save_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def extract_usage(completion) -> Dict[str, Any]:
    usage = getattr(completion, "usage", None)
    if usage is None:
        return {}
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    if isinstance(usage, dict):
        return usage
    out = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens", "input_tokens", "output_tokens"):
        if hasattr(usage, key):
            out[key] = getattr(usage, key)
    return out


def completion_token_count(usage: Dict[str, Any]) -> Optional[int]:
    value = usage.get("completion_tokens", usage.get("output_tokens"))
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def extract_answer_and_confidence(response: str) -> Tuple[str, int]:
    text = str(response or "").split("</think>")[-1]
    answer = ""
    match = re.search(
        r"(?:^|\n)\s*Answer\s*:\s*(.*?)(?=\n\s*Confidence\s*:|\Z)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match:
        answer = match.group(1).strip()
    else:
        answer_match = re.search(r"(?:final answer|answer)\s*(?:is|:)\s*(.+)", text, flags=re.IGNORECASE)
        answer = answer_match.group(1).strip() if answer_match else text.strip()

    answer = re.sub(r"^```(?:\w+)?\s*", "", answer.strip())
    answer = re.sub(r"\s*```$", "", answer.strip())

    confidence = 100
    conf_match = re.search(r"(?:^|\n)\s*Confidence\s*:\s*(\d+(?:\.\d+)?)\s*%?", text, flags=re.IGNORECASE)
    if conf_match:
        confidence = max(0, min(100, int(round(float(conf_match.group(1))))))
    return answer, confidence


def prompt_bundle(spec: DatasetSpec) -> Dict[str, str]:
    bundle = dict(spec.prompts or {})
    if not bundle.get("system_prompt"):
        raise ValueError(f"{spec.name} prompt.py must define PROMPT_BUNDLE['system_prompt']")
    bundle.setdefault("user_prompt", "{question}")
    return bundle


def format_messages(spec: DatasetSpec, sample: EvalSample, args) -> List[Dict[str, Any]]:
    bundle = prompt_bundle(spec)
    system_prompt = bundle["system_prompt"]
    user_prompt = bundle.get("user_prompt", "{question}").format(question=sample.question)
    return [
        {"role": args.system_role, "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def request_extra_body(args) -> Optional[Dict[str, Any]]:
    extra_body: Dict[str, Any] = {}
    if args.repetition_penalty is not None:
        extra_body["repetition_penalty"] = args.repetition_penalty
    if args.disable_thinking:
        extra_body["chat_template_kwargs"] = {"enable_thinking": False}
    return extra_body or None


def build_completion_kwargs(args, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {
        "model": args.model,
        "messages": messages,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "presence_penalty": args.presence_penalty,
    }
    if args.max_completion_tokens is not None:
        kwargs["max_tokens"] = args.max_completion_tokens
    if args.frequency_penalty is not None:
        kwargs["frequency_penalty"] = args.frequency_penalty
    extra_body = request_extra_body(args)
    if extra_body is not None:
        kwargs["extra_body"] = extra_body
    return kwargs


async def attempt_sample(
    spec: DatasetSpec,
    sample: EvalSample,
    args,
    client: AsyncOpenAI,
) -> Tuple[str, Dict[str, Any]]:
    messages = format_messages(spec, sample, args)
    completion_kwargs = build_completion_kwargs(args, messages)
    attempts_meta: List[Dict[str, Any]] = []
    last_content: Optional[str] = None
    last_usage: Dict[str, Any] = {}
    retry_enabled = retry_long_enabled(args)
    max_attempts = effective_retry_max_attempts(args)

    for attempt_idx in range(1, max_attempts + 1):
        try:
            completion = await client.chat.completions.create(**completion_kwargs)
            content = completion.choices[0].message.content or ""
            usage = extract_usage(completion)
            completion_tokens = completion_token_count(usage)
            too_long = (
                retry_enabled
                and
                completion_tokens is not None
                and completion_tokens > args.retry_token_threshold
            )
            attempts_meta.append(
                {
                    "attempt": attempt_idx,
                    "completion_tokens": completion_tokens,
                    "too_long": too_long,
                }
            )
            last_content = str(content)
            last_usage = usage
            if not too_long:
                break
            if attempt_idx < max_attempts:
                print(
                    "[RetryLong] "
                    f"id={sample.sample_id} attempt={attempt_idx} "
                    f"completion_tokens={completion_tokens} "
                    f"> threshold={args.retry_token_threshold}; retrying"
                )
        except Exception as exc:
            attempts_meta.append({"attempt": attempt_idx, "error": str(exc)})
            print(f"[Error] id={sample.sample_id} attempt={attempt_idx} -> {exc}")
            if attempt_idx >= max_attempts and last_content is None:
                raise

    if last_content is None:
        raise RuntimeError("model returned no content")

    retry_meta = {
        "mode": args.mode,
        "retry_long_enabled": retry_enabled,
        "retry_token_threshold": args.retry_token_threshold,
        "configured_retry_max_attempts": int(args.retry_max_attempts),
        "effective_retry_max_attempts": max_attempts,
        "attempt_count": len(attempts_meta),
        "attempts": attempts_meta,
        "final_too_long": bool(
            retry_enabled
            and
            attempts_meta
            and attempts_meta[-1].get("completion_tokens") is not None
            and attempts_meta[-1]["completion_tokens"] > args.retry_token_threshold
        ),
    }
    return last_content, {"usage": last_usage, "retry_meta": retry_meta, "messages": messages}


def make_case_dir(save_path: str, sample: EvalSample) -> str:
    now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    case_dir = os.path.join(save_path, "cases", f"{now}_row{sample.idx}")
    os.makedirs(case_dir, exist_ok=True)
    return case_dir


async def run_one(
    spec: DatasetSpec,
    sample: EvalSample,
    args,
    llm_client: AsyncOpenAI,
    judge_client: Optional[AsyncOpenAI],
    predictions: Dict[str, Any],
    predictions_lock: asyncio.Lock,
    output_path: str,
    semaphore: asyncio.Semaphore,
) -> None:
    async with semaphore:
        if not args.overwrite and str(sample.sample_id) in predictions:
            print(f"[SKIP] id={sample.sample_id} already exists in {output_path}")
            return

        case_start = time.time()
        case_dir = make_case_dir(args.save_path, sample)
        score_result = None
        raw_response = ""
        extracted_answer = ""
        confidence = 100
        meta: Dict[str, Any] = {}

        try:
            raw_response, meta = await attempt_sample(spec, sample, args, llm_client)
            extracted_answer, confidence = extract_answer_and_confidence(raw_response)

            if args.score:
                if judge_client is None:
                    raise ValueError("--score requires --judge_base_url and --judge_model")
                score_result = await score_prediction(
                    spec,
                    sample,
                    raw_response,
                    judge_client=judge_client,
                    judge_model=args.judge_model,
                )

            prediction_payload = {
                "model": args.model,
                "response": raw_response,
                "usage": meta.get("usage", {}),
                "retry_meta": meta.get("retry_meta", {}),
            }
            async with predictions_lock:
                predictions[str(sample.sample_id)] = prediction_payload
                atomic_save_json(output_path, predictions)

            temp_json = {
                "dataset_name": spec.name,
                "sample_id": sample.sample_id,
                "idx": sample.idx,
                "task_type": spec.task_type,
                "question": sample.question,
                "answer": sample.answer,
                "predicted": extracted_answer,
                "raw_response": raw_response,
                "confidence": confidence,
                "score": score_result.score if score_result is not None else None,
                "score_result": score_result.to_dict() if score_result is not None else {
                    "status": "not_scored",
                    "score": None,
                    "official_scorer": spec.scorer.get("source", ""),
                },
                "metadata": sample.metadata,
                "trajectory": meta.get("messages", []) + [{"role": "assistant", "content": raw_response}],
                "sub_traj": "",
            }
            with open(os.path.join(case_dir, "temp.json"), "w", encoding="utf-8") as f:
                json.dump(temp_json, f, ensure_ascii=False, indent=2)
            with open(os.path.join(case_dir, "temp_origin.json"), "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "origin_traj": temp_json["trajectory"],
                        "origin_sub_traj": "",
                        "token_usage": meta.get("usage", {}),
                        "retry_meta": meta.get("retry_meta", {}),
                        "case_duration_seconds": time.time() - case_start,
                        "call_stats": {
                            "assistant_calls_total": int(meta.get("retry_meta", {}).get("attempt_count") or 1),
                            "search_calls_total": 0,
                            "visit_calls_total": 0,
                        },
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            status = score_result.status if score_result is not None else "predicted"
            score = score_result.score if score_result is not None else "NA"
            print(f"[HLE-NoTool] idx={sample.idx} id={sample.sample_id} status={status} score={score}")
        except Exception as exc:
            error_trace = traceback.format_exc()
            with open(os.path.join(case_dir, "fatal_error.txt"), "w", encoding="utf-8") as f:
                f.write(f"dataset: {spec.name}\n")
                f.write(f"idx: {sample.idx}\n")
                f.write(f"sample_id: {sample.sample_id}\n")
                f.write(f"question: {sample.question}\n")
                f.write(f"error: {type(exc).__name__}: {exc}\n\n")
                f.write(error_trace)
            with open(os.path.join(case_dir, "temp.json"), "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "dataset_name": spec.name,
                        "sample_id": sample.sample_id,
                        "idx": sample.idx,
                        "task_type": spec.task_type,
                        "question": sample.question,
                        "answer": sample.answer,
                        "predicted": "",
                        "raw_response": raw_response,
                        "score": 0,
                        "score_result": {
                            "status": "error",
                            "score": None,
                            "official_scorer": spec.scorer.get("source", ""),
                            "error_type": type(exc).__name__,
                            "error_message": str(exc),
                        },
                        "metadata": sample.metadata,
                        "trajectory": meta.get("messages", []),
                        "sub_traj": "",
                        "error": {"type": type(exc).__name__, "message": str(exc), "traceback": error_trace},
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            print(f"[HLE-NoTool][ERROR] idx={sample.idx} id={sample.sample_id}: {type(exc).__name__}: {exc}")


async def run(args) -> None:
    spec = load_spec(args)
    samples = load_samples(spec, no_decrypt=args.no_decrypt)
    text_only_count = sum(1 for sample in samples if not sample_has_image(sample))
    selected = select_samples(samples, args)

    output_path = build_output_path(args)
    args.save_path = args.save_path or os.path.dirname(output_path) or "."
    os.makedirs(args.save_path, exist_ok=True)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    if args.dry_run:
        preview = selected[0] if selected else None
        print(json.dumps({
            "dataset_name": spec.name,
            "data_path": spec.data_path,
            "data_format": spec.data_format,
            "prompt_source": spec.prompt_source,
            "total_samples": len(samples),
            "text_only_samples": text_only_count,
            "selected_samples": len(selected),
            "output": output_path,
            "save_path": args.save_path,
            "generation": {
                "mode": args.mode,
                "temperature": args.temperature,
                "top_p": args.top_p,
                "presence_penalty": args.presence_penalty,
                "max_completion_tokens": args.max_completion_tokens,
                "retry_long_enabled": retry_long_enabled(args),
                "retry_token_threshold": args.retry_token_threshold,
                "configured_retry_max_attempts": args.retry_max_attempts,
                "effective_retry_max_attempts": effective_retry_max_attempts(args),
            },
            "first_sample": {
                "sample_id": preview.sample_id,
                "idx": preview.idx,
                "question_preview": preview.question[:240],
                "answer_preview": str(preview.answer)[:120],
                "metadata": preview.metadata,
            } if preview else None,
        }, ensure_ascii=False, indent=2))
        return

    predictions = load_json_dict(output_path)
    if not args.overwrite:
        before = len(selected)
        selected = [sample for sample in selected if str(sample.sample_id) not in predictions]
        print(f"Already predicted and skipped: {before - len(selected)}")
    print(f"Need to run now: {len(selected)}")
    print(f"Output predictions: {output_path}")

    if not selected:
        atomic_save_json(output_path, predictions)
        return

    llm_client = AsyncOpenAI(base_url=args.base_url, api_key=args.api_key, timeout=args.timeout)
    judge_client = None
    if args.score:
        judge_client = AsyncOpenAI(
            base_url=args.judge_base_url,
            api_key=args.judge_api_key,
            timeout=args.judge_timeout,
            max_retries=args.judge_max_retries,
        )

    try:
        semaphore = asyncio.Semaphore(max(1, args.num_threads * args.num_workers))
        lock = asyncio.Lock()
        tasks = [
            asyncio.create_task(run_one(spec, sample, args, llm_client, judge_client, predictions, lock, output_path, semaphore))
            for sample in selected
        ]
        await asyncio.gather(*tasks)
    finally:
        await llm_client.close()
        if judge_client is not None:
            await judge_client.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run HLE without tools using the raw HLE prompt format.")
    parser.add_argument("--dataset-name", "--dataset_name", dest="dataset_name", default=DEFAULT_DATASET_NAME)
    parser.add_argument("--dataset", type=str, default="", help="Local parquet/json/jsonl/csv path; kept compatible with raw HLE_predict.py")
    parser.add_argument("--dataset-path", "--dataset_path", dest="dataset_path", default="")
    parser.add_argument("--data_path", type=str, default="")
    parser.add_argument("--data-format", "--data_format", dest="data_format", default="")
    parser.add_argument("--split", type=str, default="test", help="Accepted for raw HLE_predict.py compatibility; local files are used.")
    parser.add_argument("--mode", type=str, default="direct", choices=["direct", "refine_summary"])
    parser.add_argument("--output", type=str, default="")
    parser.add_argument("--save-path", "--save_path", dest="save_path", default="")

    parser.add_argument("--base_url", "--sdk_base_url", dest="base_url", type=str, default=os.environ.get("BASE_URL", "http://127.0.0.1:38610/v1"))
    parser.add_argument("--api_key", "--sdk_api_key", dest="api_key", type=str, default=os.environ.get("API_KEY", "inspectai"))
    parser.add_argument("--model", type=str, default=os.environ.get("MODEL", "Qwen/Qwen3.5-122B-A10B"))
    parser.add_argument("--system_role", type=str, default="system", choices=["system", "user"])
    parser.add_argument("--max_completion_tokens", type=int, default=128000)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top_p", type=float, default=0.95)
    parser.add_argument("--presence_penalty", type=float, default=0.2)
    parser.add_argument("--frequency_penalty", type=float, default=None)
    parser.add_argument("--repetition_penalty", type=float, default=None)
    parser.add_argument("--disable_thinking", action="store_true")
    parser.add_argument("--timeout", type=float, default=10000.0)

    parser.add_argument("--num_threads", type=int, default=1)
    parser.add_argument("--num_workers", type=int, default=20)
    parser.add_argument("--concurrency_limit", type=int, default=None)
    parser.add_argument("--max_samples", type=int, default=None)
    parser.add_argument("--question_id", type=str, default=None)
    parser.add_argument("--question_ids", type=str, default=None)
    parser.add_argument("--target_indices", type=str, default="")
    parser.add_argument("--start_index", type=int, default=0)
    parser.add_argument("--end_index", type=int, default=2158)
    parser.add_argument("--target-shard-rank", "--target_shard_rank", dest="target_shard_rank", type=int, default=0)
    parser.add_argument("--target-shard-count", "--target_shard_count", dest="target_shard_count", type=int, default=1)
    parser.add_argument("--include-images", "--include_images", dest="include_images", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--no-decrypt", "--no_decrypt", dest="no_decrypt", action="store_true")
    parser.add_argument("--dry-run", "--dry_run", dest="dry_run", action="store_true")

    parser.add_argument("--retry_token_threshold", type=int, default=DEFAULT_RETRY_TOKEN_THRESHOLD)
    parser.add_argument("--retry_max_attempts", type=int, default=DEFAULT_RETRY_MAX_ATTEMPTS)

    parser.add_argument("--score", action="store_true", help="Score predictions inline with the HLE judge.")
    parser.add_argument("--judge_base_url", type=str, default=os.environ.get("JUDGE_BASE_URL", ""))
    parser.add_argument("--judge_api_key", type=str, default=os.environ.get("JUDGE_API_KEY", os.environ.get("API_KEY", "inspectai")))
    parser.add_argument("--judge_model", type=str, default=os.environ.get("JUDGE_MODEL", ""))
    parser.add_argument("--judge-mode", "--judge_mode", dest="judge_mode", type=str, default="local", choices=["local", "offical", "official"])
    parser.add_argument("--judge_timeout", type=float, default=600.0)
    parser.add_argument("--judge_max_retries", type=int, default=0)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.concurrency_limit is not None:
        args.num_threads = 1
        args.num_workers = args.concurrency_limit
    if args.score and (not args.judge_base_url or not args.judge_model):
        parser.error("--score requires --judge_base_url and --judge_model")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
