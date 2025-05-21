import json, subprocess, tempfile, sys, contextlib, os

@contextlib.contextmanager
def tmp_py(code: str):
    with tempfile.NamedTemporaryFile("w+", suffix=".py", delete=False) as f:
        f.write(code)
        name = f.name
    try:
        yield name
    finally:
        os.unlink(name)

def evaluate(candidate_code: str, tests: str, timeout: int = 30) -> bool:
    """코드+테스트 통과 여부 반환"""
    with tmp_py(candidate_code + "\n" + tests) as file:
        try:
            subprocess.check_output([sys.executable, file],
                                    stderr=subprocess.STDOUT, timeout=timeout)
            return True
        except subprocess.CalledProcessError:
            return False

# CLI용
if __name__ == "__main__":
    task_json, code_file = sys.argv[1:3]
    task = json.load(open(task_json))
    code = open(code_file).read()
    print(json.dumps({"passed": evaluate(code, task["test"])}))
