###############################################################################
# Snakefile – 164문제 × SINGLE/MULTI 자동 실행 + 채점
###############################################################################
import pathlib, json

TASK_IDS = [f"{i:03d}" for i in range(164)]   # 000~163
CONFIGS  = ["SINGLE", "MULTI"]
MODEL    = "gpt-4o"                           # 필요 시 변경

###############################################################################
# 0) 목표: 결과 JSON 328개
rule all:
    input:
        expand("raw_results/{cfg}/HumanEval_{tid}.json",
               cfg=CONFIGS, tid=TASK_IDS)

###############################################################################
# 1) HumanEval.jsonl → 개별 문제 파일 분리
rule split_task:
    input:
        src="data/HumanEval.jsonl"
    output:
        dst="data/tasks/HumanEval_{tid}.json"
    run:
        p = pathlib.Path(output.dst)
        p.parent.mkdir(parents=True, exist_ok=True)
        line = list(open(input.src))[int(wildcards.tid)]
        p.write_text(line)

###############################################################################
# 2) 파이프라인 실행 + 채점( runner.py 내부에서 수행 )
rule run_eval:
    input:
        task="data/tasks/HumanEval_{tid}.json"
    output:
        "raw_results/{cfg}/HumanEval_{tid}.json"
    params:
        cfg=lambda w: w.cfg,
        model=MODEL
    threads: 1
    shell:
        """
        python scripts/runner.py \
          --task {input.task} \
          --model {params.model} \
          --config {params.cfg} \
          --out {output}
        """
