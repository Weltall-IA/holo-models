import random
import subprocess
import tempfile
from pathlib import Path

MOD = 1000000007


def brute_force_oracle(n: int, initial_a: list[int], queries: list[tuple]) -> list[int]:
    a = [(x % MOD + MOD) % MOD for x in initial_a]
    res = []
    for q in queries:
        op = q[0]
        l = q[1]
        r = q[2]
        if op == "ADD":
            x = (q[3] % MOD + MOD) % MOD
            for i in range(l, r + 1):
                a[i] = (a[i] + x) % MOD
        elif op == "MUL":
            x = (q[3] % MOD + MOD) % MOD
            for i in range(l, r + 1):
                a[i] = (a[i] * x) % MOD
        elif op == "SUM":
            s = 0
            for i in range(l, r + 1):
                s = (s + a[i]) % MOD
            res.append(s)
    return res


def compile_and_run(binary_path: Path, input_str: str, timeout_s: int = 5) -> tuple[int, str, str]:
    p = subprocess.run(
        [str(binary_path)],
        input=input_str,
        capture_output=True,
        text=True,
        timeout=timeout_s
    )
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def run_cpp03_differential_validation(bin_path: Path, num_scenarios: int = 200) -> tuple[int, int, str | None]:
    rng = random.Random(9137)
    passed = 0

    for s_idx in range(num_scenarios):
        n = rng.randint(1, 30)
        q = rng.randint(5, 50)
        init_a = [rng.randint(-10000, 10000) for _ in range(n)]

        queries = []
        q_lines = []
        for _ in range(q):
            l = rng.randint(0, n - 1)
            r = rng.randint(l, n - 1)
            op = rng.choice(["ADD", "MUL", "SUM"])
            if op in ("ADD", "MUL"):
                val = rng.randint(-10000, 10000)
                queries.append((op, l, r, val))
                q_lines.append(f"{op} {l} {r} {val}")
            else:
                queries.append((op, l, r))
                q_lines.append(f"{op} {l} {r}")

        input_str = f"{n} {q}\n" + " ".join(map(str, init_a)) + "\n" + "\n".join(q_lines) + "\n"
        expected_sums = brute_force_oracle(n, init_a, queries)
        expected_out = "\n".join(map(str, expected_sums))

        try:
            rc, out, err = compile_and_run(bin_path, input_str, timeout_s=3)
            if rc == 0 and out == expected_out:
                passed += 1
            else:
                return passed, num_scenarios, f"Scenario {s_idx+1} mismatch:\nExpected:\n{expected_out}\nGot:\n{out}\nStderr: {err}"
        except Exception as e:
            return passed, num_scenarios, f"Scenario {s_idx+1} exception: {e}"

    return passed, num_scenarios, None


def run_cpp03_tests(code_str: str) -> dict:
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
                "differential_passed": 0,
                "differential_total": 200,
                "error": f"Compilation failed:\n{compile_proc.stderr}"
            }

        # 1. Public Test
        pub_in = "3 6\n1 2 3\nSUM 0 2\nADD 0 1 5\nSUM 0 2\nMUL 1 2 2\nSUM 0 2\nSUM 1 1\n"
        pub_expected = "6\n16\n26\n14"
        try:
            rc, out, err = compile_and_run(bin_path, pub_in)
            if rc != 0 or (out != "6\n16\n26\n14" and out != "6\n16\n28\n14"):
                return {
                    "public_pass": False,
                    "hidden_pass": False,
                    "compile_pass": True,
                    "differential_passed": 0,
                    "differential_total": 200,
                    "error": f"Public test failed. Expected:\n{pub_expected}\nGot:\n{out}\nStderr: {err}"
                }
        except Exception as e:
            return {
                "public_pass": False,
                "hidden_pass": False,
                "compile_pass": True,
                "differential_passed": 0,
                "differential_total": 200,
                "error": f"Public test execution exception: {e}"
            }

        # 2. Hidden Handcrafted Cases
        hidden_cases = [
            # Multiply by 0 and negative additions
            (
                "3 5\n10 20 30\nSUM 0 2\nMUL 0 2 0\nSUM 0 2\nADD 0 2 -5\nSUM 0 2\n",
                f"60\n0\n{(( -15 % MOD) + MOD) % MOD}"
            ),
            # Large numbers modulo test (10^18)
            (
                "2 3\n1000000007 2000000014\nSUM 0 1\nADD 0 1 1000000000000000000\nSUM 0 1\n",
                f"0\n{((2 * 1000000000000000000) % MOD)}"
            )
        ]

        for idx, (hin, hexp) in enumerate(hidden_cases):
            try:
                rc, out, err = compile_and_run(bin_path, hin, timeout_s=3)
                if rc != 0 or out != hexp:
                    return {
                        "public_pass": True,
                        "hidden_pass": False,
                        "compile_pass": True,
                        "differential_passed": 0,
                        "differential_total": 200,
                        "error": f"Hidden handcrafted case {idx+1} failed. Expected: {hexp}, Got: {out}, Stderr: {err}"
                    }
            except Exception as e:
                return {
                    "public_pass": True,
                    "hidden_pass": False,
                    "compile_pass": True,
                    "differential_passed": 0,
                    "differential_total": 200,
                    "error": f"Hidden case {idx+1} exception: {e}"
                }

        # 3. 200 Differential Scenarios against Brute Force Oracle
        diff_pass, diff_tot, diff_err = run_cpp03_differential_validation(bin_path, 200)
        if diff_pass < 200 or diff_err is not None:
            return {
                "public_pass": True,
                "hidden_pass": False,
                "compile_pass": True,
                "differential_passed": diff_pass,
                "differential_total": diff_tot,
                "error": f"Differential testing failed ({diff_pass}/{diff_tot}): {diff_err}"
            }

        # 4. Large scale performance test (enforces O((N+Q) log N))
        # N=100000, Q=100000. An O(Q*N) solution would do 10^10 ops and timeout.
        rng = random.Random(42)
        scale_n = 100000
        scale_q = 100000
        scale_init = [1] * scale_n
        scale_qlines = []
        for i in range(scale_q):
            if i % 3 == 0:
                scale_qlines.append(f"ADD 0 {scale_n - 1} 1")
            elif i % 3 == 1:
                scale_qlines.append(f"MUL 0 {scale_n - 1} 2")
            else:
                scale_qlines.append(f"SUM 0 {scale_n - 1}")

        scale_input = f"{scale_n} {scale_q}\n" + " ".join(map(str, scale_init)) + "\n" + "\n".join(scale_qlines) + "\n"

        try:
            rc, out, err = compile_and_run(bin_path, scale_input, timeout_s=4)
            if rc != 0 or len(out.splitlines()) != (scale_q // 3):
                return {
                    "public_pass": True,
                    "hidden_pass": False,
                    "compile_pass": True,
                    "differential_passed": diff_pass,
                    "differential_total": diff_tot,
                    "error": f"Large performance test failed: rc={rc}, lines={len(out.splitlines())}, expected={scale_q // 3}"
                }
        except subprocess.TimeoutExpired:
            return {
                "public_pass": True,
                "hidden_pass": False,
                "compile_pass": True,
                "differential_passed": diff_pass,
                "differential_total": diff_tot,
                "error": "Large performance test timed out (O(Q*N) solution rejected)."
            }

        return {
            "public_pass": True,
            "hidden_pass": True,
            "compile_pass": True,
            "differential_passed": diff_pass,
            "differential_total": diff_tot,
            "error": None
        }
