# scripts/judge.py
import json, subprocess, tempfile, textwrap, sys, os, contextlib

@contextlib.contextmanager
def tmp_py(code: str):
    """임시 파이썬 파일 작성용 컨텍스트 매니저"""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".py", delete=False) as f:
        f.write(code)
        fname = f.name
    try:
        yield fname
    finally:
        os.unlink(fname)

def evaluate(candidate_code: str, tests: str) -> bool:
    """코드 + 테스트 스텁을 실행해 통과 여부 반환"""
    with tmp_py(candidate_code + "\n" + tests) as file:
        try:
            subprocess.check_output(
                [sys.executable, file],
                stderr=subprocess.STDOUT,
                timeout=30,          # 필요 시 조정
            )
            return True
        except subprocess.CalledProcessError:
            return False

def main():
    """CLI:  python judge.py <task_json> <code_py>"""
    task_path, code_path = sys.argv[1:3]
    task = json.load(open(task_path))
    code = open(code_path).read()
    passed = evaluate(code, task["test"])
    print(json.dumps({"passed": passed}))

if __name__ == "__main__":
    main()
