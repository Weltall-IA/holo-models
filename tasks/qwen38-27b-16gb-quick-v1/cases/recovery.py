import json

RECOVERY_CASES = [
    {
        "id": "A01",
        "name": "transient_timeout_retry",
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "lookup_customer",
                    "description": "Lookup customer by exact email address.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string"}
                        },
                        "required": ["email"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_customers",
                    "description": "Search customers by name.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"}
                        },
                        "required": ["name"]
                    }
                }
            }
        ],
        "messages": [
            {"role": "user", "content": "What is the customer id of ana@example.com?"}
        ],
        "max_turns": 4,
        "evaluator": "eval_a01"
    },
    {
        "id": "A02",
        "name": "missing_file_recovery",
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read the contents of a file by full path.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Absolute file path"}
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_files",
                    "description": "List files in a directory path.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Directory path"}
                        },
                        "required": ["path"]
                    }
                }
            }
        ],
        "messages": [
            {"role": "user", "content": "Read the secret_key from the app configuration in /app/config.yaml and report its value."}
        ],
        "max_turns": 5,
        "evaluator": "eval_a02"
    },
    {
        "id": "A03",
        "name": "test_guided_correction",
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read file contents.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"}
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write new contents to a file.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"}
                        },
                        "required": ["path", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "run_tests",
                    "description": "Run the test suite and get output results.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            }
        ],
        "messages": [
            {"role": "user", "content": "Fix the bug in `math_utils.py`. First inspect the code, write the fix, run tests to verify, and fix any remaining edge cases reported by tests."}
        ],
        "max_turns": 8,
        "evaluator": "eval_a03"
    }
]

class RecoveryEnvironment:
    def __init__(self, case_id: str):
        self.case_id = case_id
        self.call_history = []
        self.step_count = 0
        
        # State for A01
        self.a01_attempts = 0
        
        # State for A02
        self.a02_fs = {
            "/app": ["config.yml", "server.py"],
            "/app/config.yml": "database_port: 5432\nenv: production\nsecret_key: k_998877\n"
        }
        
        # State for A03
        self.a03_file = 'def clamp(val, min_val, max_val):\n    return max_val\n'
        self.a03_test_passed = False

    def execute_tool(self, name: str, args: dict) -> dict:
        self.call_history.append((name, args))
        self.step_count += 1
        
        if self.case_id == "A01":
            if name == "lookup_customer":
                self.a01_attempts += 1
                if self.a01_attempts == 1:
                    return {"status": "error", "error": "TIMEOUT", "message": "Service temporarily timed out, please retry"}
                else:
                    return {"status": "ok", "id": "cus_17", "name": "Ana", "email": "ana@example.com"}
            elif name == "search_customers":
                return {"status": "ok", "results": []}
            return {"error": f"Unknown tool {name}"}
            
        elif self.case_id == "A02":
            if name == "read_file":
                p = args.get("path", "")
                if p == "/app/config.yaml":
                    return {"status": "error", "code": "ENOENT", "message": "File /app/config.yaml not found"}
                elif p in self.a02_fs:
                    return {"status": "ok", "content": self.a02_fs[p]}
                else:
                    return {"status": "error", "code": "ENOENT", "message": f"File {p} not found"}
            elif name == "list_files":
                p = args.get("path", "")
                if p == "/app" or p == "/app/":
                    return {"status": "ok", "files": ["config.yml", "server.py"]}
                return {"status": "error", "message": "Directory not found"}
            return {"error": f"Unknown tool {name}"}
            
        elif self.case_id == "A03":
            if name == "read_file":
                p = args.get("path", "")
                if "math_utils" in p:
                    return {"status": "ok", "content": self.a03_file}
                return {"error": "File not found"}
            elif name == "write_file":
                p = args.get("path", "")
                c = args.get("content", "")
                self.a03_file = c
                return {"status": "ok", "message": f"Successfully wrote {len(c)} bytes to {p}"}
            elif name == "run_tests":
                # Check code logic
                # Needs to: 1) clamp value correctly, 2) raise ValueError when min_val > max_val
                has_clamp_logic = ("min_val" in self.a03_file and "max_val" in self.a03_file and 
                                  ("min(" in self.a03_file or "<" in self.a03_file or ">" in self.a03_file))
                has_validation = ("raise ValueError" in self.a03_file or "ValueError" in self.a03_file)
                
                if not has_clamp_logic:
                    return {"status": "failed", "output": "FAILED: clamp(5, 1, 10) returned unexpected value"}
                if not has_validation:
                    return {"status": "failed", "output": "FAILED test_edge_case: clamp(5, 10, 1) did not raise ValueError. Rule: raise ValueError when min_val > max_val."}
                
                self.a03_test_passed = True
                return {"status": "passed", "output": "3 passed in 0.02s"}
            return {"error": f"Unknown tool {name}"}
            
        return {"error": "Invalid environment"}

    def evaluate(self, final_text: str) -> dict:
        if self.case_id == "A01":
            if self.a01_attempts >= 2 and "cus_17" in final_text:
                return {"success": 1, "error": None, "turns": self.step_count}
            return {"success": 0, "error": f"Failed recovery. Attempts: {self.a01_attempts}, Text: {final_text}", "turns": self.step_count}
            
        elif self.case_id == "A02":
            called_list = any(name == "list_files" for name, _ in self.call_history)
            called_read_yml = any(name == "read_file" and "config.yml" in str(args) for name, args in self.call_history)
            has_secret = "k_998877" in final_text
            if called_list and called_read_yml and has_secret:
                return {"success": 1, "error": None, "turns": self.step_count}
            return {"success": 0, "error": f"Missing recovery steps (list: {called_list}, read_yml: {called_read_yml}, secret: {has_secret})", "turns": self.step_count}
            
        elif self.case_id == "A03":
            if self.a03_test_passed:
                return {"success": 1, "error": None, "turns": self.step_count}
            return {"success": 0, "error": "Tests never passed", "turns": self.step_count}
            
        return {"success": 0, "error": "Unknown case"}
