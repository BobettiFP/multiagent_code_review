import itertools, pathlib

TASK_IDS = [f"{i:03d}" for i in range(164)]      # 000~163
CONFIGS  = ["SINGLE", "MULTI"]

rule all:
    input:
        expand("raw_results/{config}/HumanEval_{tid}.json",
               config=CONFIGS, tid=TASK_IDS)

# 이미 split_task 규칙이 있다면 그대로 사용
rule split_task:
    input:  "data/HumanEval.jsonl"
    output: "data/tasks/HumanEval_{tid}.json"
    run:
        p = pathlib.Path(output[0]); p.parent.mkdir(parents=True, exist_ok=True)
        line = list(open(input[0]))[int(wildcards.tid)]
        p.write_text(line)

rule run_eval:
    input:
        task="data/tasks/HumanEval_{tid}.json"
    output:
        "raw_results/{config}/HumanEval_{tid}.json"
    params:
        model="gpt-4o"           # 필요하면 다른 모델이나 변수로
    threads: 1                   # OpenAI 호출은 네트워크 bound
    shell:
        """
        python scripts/runner.py \
            --task {input.task} \
            --model {params.model} \
            --config {wildcards.config} \
            --out {output}
        """
