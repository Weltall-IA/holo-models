import json

TOOL_CASES = [
    {
        "id": "T01",
        "name": "exact_lookup",
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "lookup_customer",
                    "description": "Lookup a customer profile by their exact email address.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string", "description": "The exact email address"}
                        },
                        "required": ["email"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_customers",
                    "description": "Fuzzy search customers by full or partial name.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Customer name to search for"}
                        },
                        "required": ["name"]
                    }
                }
            }
        ],
        "messages": [
            {"role": "user", "content": "Find the customer whose exact email is ana@example.com."}
        ],
        "type": "single_turn",
        "evaluator": "eval_t01"
    },
    {
        "id": "T02",
        "name": "two_step_subscription_lookup",
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "lookup_customer",
                    "description": "Lookup customer by email.",
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
                    "name": "get_subscription",
                    "description": "Get the active subscription and plan details for a customer ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "customer_id": {"type": "string"}
                        },
                        "required": ["customer_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "cancel_subscription",
                    "description": "Cancel a customer's subscription.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "subscription_id": {"type": "string"}
                        },
                        "required": ["subscription_id"]
                    }
                }
            }
        ],
        "messages": [
            {"role": "user", "content": "Tell me the active plan for ana@example.com. Do not change anything."}
        ],
        "type": "multi_turn",
        "mock_responses": {
            "lookup_customer": {"id": "cus_17", "name": "Ana", "email": "ana@example.com"},
            "get_subscription": {"subscription_id": "sub_99", "plan": "Pro", "status": "active"}
        },
        "evaluator": "eval_t02"
    },
    {
        "id": "T03",
        "name": "choose_refund_not_cancel",
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_invoice",
                    "description": "Retrieve invoice details by invoice ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "invoice_id": {"type": "string"}
                        },
                        "required": ["invoice_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "refund_invoice",
                    "description": "Refund an invoice in full or partially (amount in cents).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "invoice_id": {"type": "string"},
                            "amount_cents": {"type": "integer", "description": "Refund amount in cents, e.g. 2500 for R$ 25.00"}
                        },
                        "required": ["invoice_id", "amount_cents"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "cancel_subscription",
                    "description": "Cancel a recurring subscription.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "subscription_id": {"type": "string"}
                        },
                        "required": ["subscription_id"]
                    }
                }
            }
        ],
        "messages": [
            {"role": "user", "content": "Refund exactly R$ 25.00 on invoice inv_9 and keep the subscription active."}
        ],
        "type": "multi_turn",
        "mock_responses": {
            "get_invoice": {"invoice_id": "inv_9", "total_cents": 5000, "status": "paid", "customer_id": "cus_17"}
        },
        "evaluator": "eval_t03"
    },
    {
        "id": "T04",
        "name": "no_unnecessary_tool",
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "lookup_customer",
                    "description": "Lookup customer by email.",
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
                    "name": "get_subscription",
                    "description": "Get subscription info.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "customer_id": {"type": "string"}
                        },
                        "required": ["customer_id"]
                    }
                }
            }
        ],
        "messages": [
            {"role": "user", "content": "The active plan is Pro. Answer only with the plan name; do not perform any lookup."}
        ],
        "type": "single_turn",
        "evaluator": "eval_t04"
    },
    {
        "id": "T05",
        "name": "strict_structured_call",
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "create_ticket",
                    "description": "Create a support/incident ticket with structured priority and tags.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Title of the ticket"},
                            "priority": {"type": "string", "enum": ["low", "medium", "high"], "description": "Priority level"},
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of tags associated with the ticket"
                            }
                        },
                        "required": ["title", "priority", "tags"]
                    }
                }
            }
        ],
        "messages": [
            {"role": "user", "content": "Create a high-priority ticket titled \"Checkout timeout\" tagged checkout and payments."}
        ],
        "type": "single_turn",
        "evaluator": "eval_t05"
    }
]

def eval_t01(tool_calls, final_text) -> dict:
    if not tool_calls:
        return {"success": 0, "error": "No tool called"}
    first = tool_calls[0]
    fn_name = first.get("function", {}).get("name")
    args_str = first.get("function", {}).get("arguments", "{}")
    if fn_name != "lookup_customer":
        return {"success": 0, "error": f"Wrong tool called: {fn_name}"}
    try:
        args = json.loads(args_str) if isinstance(args_str, str) else args_str
    except Exception as e:
        return {"success": 0, "error": f"Invalid JSON in tool args: {args_str}"}
    if args.get("email") == "ana@example.com":
        return {"success": 1, "error": None}
    return {"success": 0, "error": f"Incorrect email argument: {args}"}

def eval_t02(tool_calls, final_text) -> dict:
    # Expected sequence: lookup_customer -> get_subscription. Never cancel_subscription.
    names = [call.get("function", {}).get("name") for call in tool_calls]
    if "cancel_subscription" in names:
        return {"success": 0, "error": "Forbidden tool cancel_subscription called"}
    if "lookup_customer" not in names or "get_subscription" not in names:
        return {"success": 0, "error": f"Missing expected tool call sequence. Called: {names}"}
    
    # Check customer_id passed to get_subscription
    for call in tool_calls:
        if call.get("function", {}).get("name") == "get_subscription":
            args = call.get("function", {}).get("arguments", "{}")
            if isinstance(args, str):
                try: args = json.loads(args)
                except: pass
            if args.get("customer_id") != "cus_17":
                return {"success": 0, "error": f"Wrong customer_id passed: {args}"}
    return {"success": 1, "error": None}

def eval_t03(tool_calls, final_text) -> dict:
    names = [call.get("function", {}).get("name") for call in tool_calls]
    if "cancel_subscription" in names:
        return {"success": 0, "error": "Forbidden tool cancel_subscription called"}
    
    refund_calls = [c for c in tool_calls if c.get("function", {}).get("name") == "refund_invoice"]
    if not refund_calls:
        return {"success": 0, "error": "refund_invoice was never called"}
    
    call = refund_calls[0]
    args = call.get("function", {}).get("arguments", "{}")
    if isinstance(args, str):
        try: args = json.loads(args)
        except: pass
    if args.get("invoice_id") == "inv_9" and args.get("amount_cents") == 2500:
        return {"success": 1, "error": None}
    return {"success": 0, "error": f"Incorrect refund arguments: {args}"}

def eval_t04(tool_calls, final_text) -> dict:
    if tool_calls and len(tool_calls) > 0:
        return {"success": 0, "error": f"Unnecessary tool called: {[c.get('function', {}).get('name') for c in tool_calls]}"}
    if "pro" in final_text.lower():
        return {"success": 1, "error": None}
    return {"success": 0, "error": f"Final text did not mention 'Pro': {final_text}"}

def eval_t05(tool_calls, final_text) -> dict:
    if not tool_calls:
        return {"success": 0, "error": "No tool called"}
    call = tool_calls[0]
    fn_name = call.get("function", {}).get("name")
    if fn_name != "create_ticket":
        return {"success": 0, "error": f"Wrong tool: {fn_name}"}
    args_str = call.get("function", {}).get("arguments", "{}")
    try:
        args = json.loads(args_str) if isinstance(args_str, str) else args_str
    except Exception as e:
        return {"success": 0, "error": f"Invalid JSON in args: {args_str}"}
    
    title_ok = args.get("title") == "Checkout timeout"
    priority_ok = args.get("priority") == "high"
    raw_tags = args.get("tags", [])
    tags_set = set(t.lower() for t in raw_tags) if isinstance(raw_tags, list) else set()
    tags_ok = tags_set == {"checkout", "payments"}
    
    if title_ok and priority_ok and tags_ok:
        return {"success": 1, "error": None}
    return {"success": 0, "error": f"Arguments mismatch: {args}"}
