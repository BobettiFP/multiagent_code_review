import os, json, argparse, time, openai, yaml, uuid
from pathlib import Path
from datetime import datetime
# scripts/runner.py
from dotenv import load_dotenv
import os, openai   # ← openai도 같이 불러오면 편함

load_dotenv()                       # .env → 환경변수 등록
openai.api_key = os.environ["OPENAI_API_KEY"]

def load_prompt(role_file: str) -> dict:
    prm = yaml.safe_load(open(role_file))
    return {"role": "system", "content": prm["system"]}, {"role": "user", "content": prm["user"]}

def call_openai(model, messages, max_tokens=1024):
    resp = openai.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content, resp.usage.total_tokens

def single_loop(task, model, prompt_files):
    sys_msg, user_tpl = load_prompt(prompt_files[0])
    messages = [sys_msg, {"role": "user", "content": user_tpl["content"].format(**task)}]
    answer, tok = call_openai(model, messages)
    return answer, tok, messages + [{"role": "assistant", "content": answer}]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--config", choices=["SINGLE","MULTI"], default="SINGLE")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", help="결과를 저장할 경로")

    args = ap.parse_args()

    task = json.load(open(args.task))    # sample: 첫 줄만
    answer, tok, chat = single_loop(task, args.model, ["prompts/coder.yml"])

    if args.dry_run:
        print(answer[:500])
        return
    if args.config == "SINGLE":
        code, tok, chat = single_loop(task, args.model, ["prompts/coder.yml"])
    elif args.config == "MULTI":
        code, tok, chat = multi_loop(task, args.model)
    else:
        raise ValueError("알 수 없는 config")

    # --out 지정 시 그곳에 바로 저장, 없으면 타임스탬프 폴더
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        out_file = Path(args.out)
    else:
        run_id  = datetime.now().strftime("%Y%m%d-%H%M%S")+"-"+uuid.uuid4().hex[:6]
        out_dir = Path("raw_results")/run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir/"result.json"

    json.dump({"task_id": task["task_id"], "code": answer, "tokens": tok, "chat": chat}, open(out_file, "w"), ensure_ascii=False, indent=2)
def multi_loop(task, model):
    # 1) 가이드 → 배경지식
    sys_g, usr_g = load_prompt("prompts/guide.yml")
    guide_msg = [
        sys_g,
        {"role": "user", "content": usr_g["content"].format(**task)}
    ]
    guide_out, tok_g = call_openai(model, guide_msg)

    # 2) 코더 → 최초 코드
    sys_c, usr_c = load_prompt("prompts/coder.yml")
    coder_in = [
        sys_c,
        {"role": "user", "content": usr_c["content"].format(**task)},
        {"role": "assistant", "content": guide_out}
    ]
    code1, tok_c1 = call_openai(model, coder_in)

    # 3) 리뷰어 → 피드백
    sys_r, usr_r = load_prompt("prompts/reviewer.yml")
    rev_in = [
        sys_r,
        {"role": "user", "content": usr_r["content"].format(candidate_code=code1)}
    ]
    review, tok_r = call_openai(model, rev_in)

    # 4) 코더 → 최종 코드
    coder_fix_in = coder_in + [
        {"role": "assistant", "content": review}
    ]
    code2, tok_c2 = call_openai(model, coder_fix_in)

    total_tok = tok_g + tok_c1 + tok_r + tok_c2
    chat_log = guide_msg + \
               [{"role":"assistant","content":guide_out}] + \
               coder_in[1:] + [{"role":"assistant","content":code1}] + \
               rev_in + [{"role":"assistant","content":review}] + \
               [{"role":"assistant","content":code2}]
    return code2, total_tok, chat_log


if __name__ == "__main__":
    main()
