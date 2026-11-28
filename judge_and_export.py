import json
import os
import time
import requests

# ========== 配置区 ==========
API_URL = "https://api.deepseek.com/v1/chat/completions"
API_KEY = "sk-3058833f2c3b4322ab1a59feb3c542dc"
TRACE_FILE = "./mcp_traces.jsonl"
BASE_OUTPUT = "./outputs"
MODEL_NAME = "deepseek-flash"
# ============================

def llm_judge(query, trace, rubric):
    prompt = f"""
你是Agent工具调用评审专家，严格按照评分规则打分。
满分 10 分：正确识别意图、调用正确工具、参数无误、结果准确
6~9分：大体正确，存在轻微瑕疵
1~5分：工具选错 / 参数错误
0分：完全不调用工具，直接瞎回答

用户问题：{query}
Agent完整会话Trace：{json.dumps(trace, ensure_ascii=False)}
评分标准：{rubric}

⚠️ 只输出严格JSON，**不要任何多余文字、解释、markdown**
格式：{{"score": 分数, "reason": "简短理由"}}
"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "stream": False
    }
    resp = requests.post(API_URL, headers=headers, json=payload, timeout=80)
    resp.raise_for_status()
    raw_content = resp.json()["choices"][0]["message"]["content"].strip()
    return json.loads(raw_content)

def main():
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(BASE_OUTPUT, ts)

    # 适配 EvalScope 扫描结构
    model_name_full = MODEL_NAME + "-judge"
    report_dir = os.path.join(out_dir, "reports", model_name_full)
    cfg_dir = os.path.join(out_dir, "configs")
    pred_dir = os.path.join(out_dir, "predictions", model_name_full)
    review_dir = os.path.join(out_dir, "reviews", model_name_full)
    
    os.makedirs(report_dir, exist_ok=True)
    os.makedirs(cfg_dir, exist_ok=True)
    os.makedirs(pred_dir, exist_ok=True)
    os.makedirs(review_dir, exist_ok=True)

    with open(TRACE_FILE, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]

    pred_list = []
    review_list = []
    score_list = []
    
    for idx, line in enumerate(lines):
        item = json.loads(line)
        print(f"[{idx+1}/{len(lines)}] judging: {item['query']}")
        try:
            res = llm_judge(item["query"], item["trace"], item["judge_rubric"])
        except Exception as e:
            print(f"Judge失败 {idx}: {e}")
            res = {"score": 0, "reason": f"judge调用异常：{str(e)}"}
        
        score_list.append(res["score"])
        
        model_text = f"【Agent Trace】\n{json.dumps(item['trace'], ensure_ascii=False, indent=2)}\n\n【评分结果】\n得分：{res['score']}\n理由：{res['reason']}"

        # 1. 构造 predictions 结构
        sample_out = {
            "index": idx,
            "model": model_name_full,
            "model_output": {
                "choices": [
                    {
                        "message": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": model_text
                                }
                            ],
                            "role": "assistant"
                        }
                    }
                ]
            },
            "messages": [
                {
                    "role": "user",
                    "content": item["query"]
                },
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": model_text
                        }
                    ]
                }
            ],
            "agent_trace": item["trace"],
            "metadata": {
                "target": item["target_tool"],
                "judge_score": res["score"],
                "judge_reason": res["reason"]
            },
            "score": res["score"]
        }
        pred_list.append(sample_out)

        # 2. 构造 reviews 结构
        review_out = {
            "index": idx,
            "sample_score": {
                "sample_id": f"s{idx}",
                "score": {
                    "value": {
                        "acc": res["score"]
                    }
                }
            }
        }
        review_list.append(review_out)

    # 写入预测文件
    pred_path = os.path.join(pred_dir, "mcp_trace_bench_main.jsonl")
    with open(pred_path, "w", encoding="utf-8") as f:
        for rec in pred_list:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # 写入 review 文件
    review_path = os.path.join(review_dir, "mcp_trace_bench_main.jsonl")
    with open(review_path, "w", encoding="utf-8") as f:
        for rec in review_list:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # ===== EvalScope v1.15.0 原生报告结构 =====
    num_samples = len(score_list)
    avg_score = sum(score_list) / num_samples if num_samples > 0 else 0.0
    pass_cnt = sum(1 for s in score_list if s >= 6)

    report = {
        "schema_version": 2,
        "name": f"{model_name_full}@mcp_trace_bench",
        "dataset_name": "mcp_trace_bench",
        "dataset_pretty_name": "MCP Trace Bench",
        "dataset_description": "Agent Tool Calling Evaluation Benchmark",
        "model_name": model_name_full,
        "metrics": [
            {
                "identity": {
                    "name": "acc",
                    "aggregation": "mean",
                    "dimensions": {}
                },
                "legacy_name": None,
                "num": num_samples,
                "num_correct": pass_cnt, 
                "score": round(avg_score, 2),
                "macro_score": round(avg_score, 2),
                "categories": [
                    {
                        "name": ["default"],
                        "num": num_samples,
                        "num_correct": pass_cnt,
                        "score": round(avg_score, 2),
                        "macro_score": round(avg_score, 2),
                        "subsets": [
                            {
                                "name": "main",
                                "score": round(avg_score, 2),
                                "num": num_samples,
                                "num_correct": pass_cnt,
                                "metadata": None,
                                "is_aggregate": False
                            }
                        ]
                    }
                ],
                "semantics": {
                    "semantic_id": "quality.score.rating",
                    "metric_name": "Average Score",
                    "display_name": None,
                    "kind": "quality",
                    "direction": "higher_is_better",
                    "raw_unit": None,
                    "value_range": {"min": 0.0, "max": 10.0},
                    "display_kind": "number",
                    "display_multiplier": None,
                    "display_unit": "score",
                    "display_precision": 2
                }
            }
        ],
        "analysis": "N/A",
        "perf_metrics": {},
        "primary_metric_identity": {
            "name": "acc",
            "aggregation": "mean",
            "dimensions": {}
        },
        "primary_metric_unavailable_reason": None,
        "judge_summary": None,
        "execution_summary": {
            "requested": num_samples,
            "succeeded": num_samples,
            "errored": 0,
            "incomplete": False,
            "subsets": {
                "main": {
                    "requested": num_samples,
                    "succeeded": num_samples,
                    "errored": 0
                }
            }
        },
        "num": num_samples
    }

    report_path = os.path.join(report_dir, "mcp_trace_bench.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=4)

    yaml_path = os.path.join(cfg_dir, "task_config.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(f"""dataset_name: mcp_trace_bench
model_name: {model_name_full}
eval_type: custom
""")

    # ===== 新版 API：通过 diagnose_run 生成 HTML 报告 (参数名修正为 config) =====
    try:
        from evalscope.analysis import diagnose_run
        from evalscope.api.analysis import AnalysisReportConfig

        # 参数名改为 config
        config = AnalysisReportConfig(level='facts')
        diagnose_run(run_dir=out_dir, config=config)
        print(f"✅ HTML 报告已通过 diagnose_run 更新")
    except Exception as e:
        print(f"⚠️ HTML 报告生成失败（不影响看板浏览）: {e}")
    # ==========================================

    print(f"\n✅ 评测完成，结果目录：{out_dir}")
    print(f"报告文件: {report_path}")
    print(f"预测明细: {pred_path}")
    print(f"评测明细: {review_path}")

if __name__ == "__main__":
    main()