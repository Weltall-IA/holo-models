import random
import subprocess
import tempfile
from pathlib import Path


def compile_and_run(binary_path: Path, input_str: str, timeout_s: int = 5) -> tuple[int, str, str]:
    p = subprocess.run(
        [str(binary_path)],
        input=input_str,
        capture_output=True,
        text=True,
        timeout=timeout_s
    )
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def run_cpp02_tests(code_str: str) -> dict:
    with tempfile.TemporaryDirectory() as td:
        src_path = Path(td) / "solution.cpp"
        bin_path = Path(td) / "solution"
        src_path.write_text(code_str, encoding="utf-8")

        # Compile
        compile_proc = subprocess.run(
            ["g++", "-std=c++20", "-O2", "-Wall", "-Wextra", str(src_path), "-o", str(bin_path)],
            capture_output=True,
            text=True,
            timeout=15
        )

        if compile_proc.returncode != 0:
            return {
                "public_pass": False,
                "hidden_pass": False,
                "compile_pass": False,
                "error": f"Compilation failed:\n{compile_proc.stderr}"
            }

        # 1. Public Test
        pub_in = "5 3\n1 2 3 4 5\n"
        pub_expected = "6 1 3\n9 2 4\n12 3 5"
        try:
            rc, out, err = compile_and_run(bin_path, pub_in)
            if rc != 0 or out != pub_expected:
                return {
                    "public_pass": False,
                    "hidden_pass": False,
                    "compile_pass": True,
                    "error": f"Public test failed. Expected:\n{pub_expected}\nGot:\n{out}\nStderr: {err}"
                }
        except Exception as e:
            return {
                "public_pass": False,
                "hidden_pass": False,
                "compile_pass": True,
                "error": f"Public test execution exception: {e}"
            }

        # 2. Hidden Tests
        hidden_cases = [
            # k == n
            ("4 4\n10 20 30 40\n", "100 10 40"),
            # k == 1
            ("3 1\n5 2 8\n", "5 5 5\n2 2 2\n8 8 8"),
            # Invalid k <= 0
            ("5 0\n1 2 3 4 5\n", "INVALID"),
            ("5 -2\n1 2 3 4 5\n", "INVALID"),
            # Invalid k > n
            ("3 5\n1 2 3\n", "INVALID"),
            # Negative values
            ("5 3\n-5 10 -2 -8 4\n", "3 -5 10\n0 -8 10\n-6 -8 4"),
            # 64-bit sum overflow check: 5 elements of 10^9, k=3 -> sum = 3*10^9 (overflows 32-bit int)
            (
                "5 3\n1000000000 1000000000 1000000000 1000000000 1000000000\n",
                "3000000000 1000000000 1000000000\n3000000000 1000000000 1000000000\n3000000000 1000000000 1000000000"
            )
        ]

        # Scaled performance test (enforcing O(N) / O(N log K))
        # N=100000, K=25000. An O(N*K) solution would do 2.5 * 10^9 ops and timeout (> 5s).
        rng = random.Random(9137)
        scale_n = 100000
        scale_k = 25000
        scale_data = [rng.randint(-1000, 1000) for _ in range(scale_n)]
        
        # Compute expected first and last line of sliding window
        # First window: indices [0, 24999]
        w1 = scale_data[:scale_k]
        exp_first = f"{sum(w1)} {min(w1)} {max(w1)}"
        # Last window: indices [scale_n - scale_k, scale_n - 1]
        w_last = scale_data[scale_n - scale_k:]
        exp_last = f"{sum(w_last)} {min(w_last)} {max(w_last)}"

        scale_input_str = f"{scale_n} {scale_k}\n" + " ".join(map(str, scale_data)) + "\n"

        for idx, (hin, hexp) in enumerate(hidden_cases):
            try:
                rc, out, err = compile_and_run(bin_path, hin, timeout_s=4)
                if rc != 0 or out != hexp:
                    return {
                        "public_pass": True,
                        "hidden_pass": False,
                        "compile_pass": True,
                        "error": f"Hidden case {idx+1} failed. Expected:\n{hexp[:200]}\nGot:\n{out[:200]}\nStderr: {err}"
                    }
            except subprocess.TimeoutExpired:
                return {
                    "public_pass": True,
                    "hidden_pass": False,
                    "compile_pass": True,
                    "error": f"Hidden case {idx+1} timed out."
                }
            except Exception as e:
                return {
                    "public_pass": True,
                    "hidden_pass": False,
                    "compile_pass": True,
                    "error": f"Hidden case {idx+1} exception: {e}"
                }

        # Run scale test
        try:
            rc, out, err = compile_and_run(bin_path, scale_input_str, timeout_s=4)
            lines = out.splitlines()
            expected_line_count = scale_n - scale_k + 1
            if rc != 0 or len(lines) != expected_line_count or lines[0] != exp_first or lines[-1] != exp_last:
                return {
                    "public_pass": True,
                    "hidden_pass": False,
                    "compile_pass": True,
                    "error": f"Scale performance test failed. Line count: {len(lines)} (expected {expected_line_count}). First: '{lines[0] if lines else ''}' (expected '{exp_first}'). Last: '{lines[-1] if lines else ''}' (expected '{exp_last}')."
                }
        except subprocess.TimeoutExpired:
            return {
                "public_pass": True,
                "hidden_pass": False,
                "compile_pass": True,
                "error": "Scale performance test timed out (complexity O(N*K) rejected)."
            }

        return {"public_pass": True, "hidden_pass": True, "compile_pass": True, "error": None}
