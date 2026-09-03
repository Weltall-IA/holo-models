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


def run_cpp01_tests(code_str: str) -> dict:
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
        pub_in = "5\n5 7\n1 2\n3 4\n10 10\n12 14\n"
        pub_expected = "3\n1 7\n10 10\n12 14"
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
            # Zero elements
            ("0\n", "0"),
            # Single element
            ("1\n42 42\n", "1\n42 42"),
            # Invalid range l > r
            ("3\n1 5\n8 3\n10 12\n", "INVALID"),
            # Negative numbers and adjacent chain
            ("4\n-10 -5\n-4 -1\n0 5\n6 10\n", "1\n-10 10"),
            # Nested and duplicate
            ("4\n1 100\n10 20\n30 40\n1 100\n", "1\n1 100"),
            # Extreme 64-bit boundaries (INT64_MIN, INT64_MAX)
            (
                "3\n-9223372036854775808 -9223372036854775800\n0 10\n9223372036854775800 9223372036854775807\n",
                "3\n-9223372036854775808 -9223372036854775800\n0 10\n9223372036854775800 9223372036854775807"
            ),
            # Full span
            ("2\n-9223372036854775808 0\n1 9223372036854775807\n", "1\n-9223372036854775808 9223372036854775807"),
            # Touching at INT64_MAX boundary without overflow
            ("2\n9223372036854775806 9223372036854775807\n9223372036854775807 9223372036854775807\n", "1\n9223372036854775806 9223372036854775807")
        ]

        # Scaled performance test: 50,000 ranges
        scale_in = ["50000"]
        for i in range(50000):
            scale_in.append(f"{i * 2} {i * 2 + 1}") # each is [2i, 2i+1], adjacent to [2i+2, 2i+3] -> all merge into [0, 100001]
        scale_input_str = "\n".join(scale_in) + "\n"
        hidden_cases.append((scale_input_str, "1\n0 99999"))

        for idx, (hin, hexp) in enumerate(hidden_cases):
            try:
                rc, out, err = compile_and_run(bin_path, hin, timeout_s=6)
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

        return {"public_pass": True, "hidden_pass": True, "compile_pass": True, "error": None}
