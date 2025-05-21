# scripts/runner.py
import argparse, json, os, re, uuid
from datetime import datetime
from pathlib import Path

import openai, yaml
from dotenv import load_dotenv
from judge import evaluate                     # ★ 평가 함수

# ── 환경 변수 로드 ─────────────────────────────────────
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise RuntimeError("OPENAI_API_KEY 환경변수가 없습니다.")

# ── 유틸 ──────────────────────────────────────────────
def strip_fence(text: str) -> str:
    """ ```python … ``` 펜스 제거 """
    m = re.search(r"```(?:python)?\s*(.*?)```", text, flags=re.S)
    return m.group(1).strip() if m else text.strip()

def load_prompt(path: str):
    prm = yaml.safe_load(open(path))
    return {"role": "system", "content": prm["system"]}, \
           {"role": "user",   "content": prm["user"]}

def call_openai(model: str, messages: list, max_tokens: int = 1024):
    resp = openai.chat.completions.create(
        model=model, messages=messages,
        temperature=0.2, max_tokens=max_tokens)
    return resp.choices[0].message.content, resp.usage.total_tokens

# ── SINGLE / MULTI 루프 ──────────────────────────────
def single_loop(task: dict, model: str) -> tuple:
    sys_msg, user_tpl = load_prompt("prompts/coder.yml")
    messages = [sys_msg,
                {"role": "user", "content": user_tpl["content"].format(**task)}]
    code_raw, tok = call_openai(model, messages)
    return code_raw, tok, messages + [{"role": "assistant", "content": code_raw}]

def multi_loop(task: dict, model: str) -> tuple:
    # 1) Guide
    sys_g, usr_g = load_prompt("prompts/guide.yml")
    guide_msg = [sys_g,
                 {"role": "user", "content": usr_g["content"].format(**task)}]
    guide_out, tok_g = call_openai(model, guide_msg)

    # 2) Coder 초기 코드
    sys_c, usr_c = load_prompt("prompts/coder.yml")
    coder_in = [sys_c,
                {"role": "user", "content": usr_c["content"].format(**task)},
                {"role": "assistant", "content": guide_out}]
    code1, tok_c1 = call_openai(model, coder_in)

    # 3) Reviewer
    sys_r, usr_r = load_prompt("prompts/reviewer.yml")
    rev_in = [sys_r,
              {"role": "user", "content": usr_r["content"].format(
                                            candidate_code=code1)}]
    review, tok_r = call_openai(model, rev_in)

    # 4) Coder 수정본
    coder_fix = coder_in + [{"role": "assistant", "content": review}]
    code2, tok_c2 = call_openai(model, coder_fix)

    total_tok = tok_g + tok_c1 + tok_r + tok_c2
    chat_log = guide_msg + [{"role":"assistant","content":guide_out}] + \
               coder_in[1:] + [{"role":"assistant","content":code1}] + \
               rev_in + [{"role":"assistant","content":review}] + \
               [{"role":"assistant","content":code2}]
    return code2, total_tok, chat_log

# ── main ─────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--task", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--config", choices=["SINGLE", "MULTI"], default="SINGLE")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--out", help="JSON 저장 경로")
    args = p.parse_args()

    task = json.load(open(args.task))
    if args.config == "SINGLE":
        raw_code, toks, chat = single_loop(task, args.model)
    else:
        raw_code, toks, chat = multi_loop(task, args.model)

    clean_code = strip_fence(raw_code)

    if args.dry_run:
        print(clean_code[:600])
        return

    # 통과 여부 판정
    passed = evaluate(clean_code, task["test"])

    # 저장 위치 결정
    out_path = Path(args.out) if args.out else \
               Path("raw_results") / f"{datetime.now():%Y%m%d-%H%M%S}_{uuid.uuid4().hex[:6]}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    json.dump({
        "task_id": task["task_id"],
        "config": args.config,
        "passed": passed,
        "tokens": toks,
        "code": clean_code,
        "chat": chat
    }, open(out_path, "w"), ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
