"""pushbuild-mcp: a local stdio MCP server for the Pushbuild data APIs (https://pushbuild.com/apis).

Tools: search_apis (keyword search over the catalog), describe_api (one API's inputs from its OpenAPI spec)
and call_api (runs it through the REST API with your key). Standard library only.
"""
import json, os, re, sys, urllib.error, urllib.request

__version__ = "0.2.1"
BASE = os.environ.get("PUSHBUILD_BASE_URL", "https://api.pushbuild.com")
KEY = os.environ.get("PUSHBUILD_API_KEY", "")
SIGNUP = "https://pushbuild.com/apis/app/signup"
MAX_TEXT = 60000
PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
RO = {"readOnlyHint": True, "openWorldHint": True}

TOOLS = [
    {"name": "search_apis", "title": "Search APIs", "annotations": dict(RO, title="Search APIs"),
     "description": "Find Pushbuild data APIs by keyword (e.g. 'campaign contributions texas', 'restaurant inspections', 'sec 13f'). Returns API ids and what each covers. No key needed.",
     "inputSchema": {"type": "object", "properties": {"query": {"type": "string", "description": "Keywords."},
                     "limit": {"type": "integer", "description": "Max results (default 10)."}}, "required": ["query"]}},
    {"name": "describe_api", "title": "Describe an API", "annotations": dict(RO, title="Describe an API"),
     "description": "Show how to call one API before running it: its name, summary, input parameters (JSON Schema with types, enums and defaults) and docs link. Use after search_apis and before call_api. Read-only, no key needed, no usage charged.",
     "inputSchema": {"type": "object", "properties": {"api": {"type": "string", "description": "API id exactly as search_apis returned it (lowercase, hyphenated), e.g. restaurant-inspections."}}, "required": ["api"]}},
    {"name": "call_api", "title": "Run an API", "annotations": dict(RO, title="Run an API"),
     "description": "Run one API with parameters from describe_api and return JSON records (default 20; set maxItems up to 500). Needs PUSHBUILD_API_KEY (free key with monthly free usage: " + SIGNUP + ").",
     "inputSchema": {"type": "object", "properties": {"api": {"type": "string", "description": "API id."},
                     "params": {"type": "object", "description": "Input parameters for that API, as describe_api lists them."}}, "required": ["api", "params"]}},
]


def http(method, path, body=None, key=None):
    h = {"User-Agent": f"pushbuild-mcp/{__version__}", "Accept": "application/json"}
    if key:
        h["X-API-Key"] = key
    data = None
    if body is not None:
        data, h["Content-Type"] = json.dumps(body).encode(), "application/json"
    req = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            raw = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            msg = json.loads(raw).get("detail") or raw
        except ValueError:
            msg = raw
        raise RuntimeError(f"HTTP {e.code}: {msg}") from None
    return raw if path.endswith(".txt") else json.loads(raw)


_catalog, _specs = None, {}


def catalog():
    """[(id, name, summary)] parsed from the public llms.txt index, fetched once per session."""
    global _catalog
    if _catalog is None:
        rx = re.compile(r"^- \[(.+?)\]\(https://pushbuild\.com/apis/([a-z0-9-]+)\.html\): (.*?)(?: OpenAPI: \S+)?$")
        _catalog = [(m[2], m[1], m[3]) for m in map(rx.match, http("GET", "/llms.txt").splitlines()) if m]
    return _catalog


def spec(api):
    if api not in _specs:
        _specs[api] = http("GET", f"/openapi/{api}.json")
    return _specs[api]


def schema(api):
    op = spec(api)["paths"][f"/{api}/run"]["post"]
    return op["requestBody"]["content"]["application/json"]["schema"]


def search_apis(query, limit=10):
    words = [w for w in re.findall(r"[a-z0-9]+", (query or "").lower()) if len(w) > 1]
    scored = []
    for api, name, summary in catalog():
        head, text = f"{api} {name}".lower(), f"{api} {name} {summary}".lower()
        hit = [w for w in words if re.search(rf"\b{w}", text)]
        score = 10 * len(hit) + sum(3 for w in hit if re.search(rf"\b{w}", head))
        if score or not words:
            scored.append((-score, api, {"api": api, "name": name, "summary": summary, "docs": f"https://pushbuild.com/apis/{api}.html"}))
    return [c for _, _, c in sorted(scored)[: max(1, min(int(limit or 10), 50))]]


def describe_api(api):
    known = {a: (n, s) for a, n, s in catalog()}
    if api not in known:
        raise ValueError(f"Unknown API '{api}'. Use search_apis to find one.")
    return {"api": api, "name": known[api][0], "summary": known[api][1], "input": schema(api), "docs": f"https://pushbuild.com/apis/{api}.html"}


def call_api(api, params):
    if not KEY:
        raise ValueError(f"Set PUSHBUILD_API_KEY to run APIs (free key: {SIGNUP}). search_apis and describe_api work without one.")
    props = schema(api).get("properties") or {}
    bad = [p for p in (params or {}) if p not in props and p != "maxItems"]
    if bad:
        raise ValueError(f"Unknown parameter(s) for {api}: {', '.join(bad)}. Valid: {', '.join(props)}.")
    body = dict(params or {})
    body.setdefault("maxItems", 20)
    out = http("POST", f"/{api}/run", body, KEY)
    text = json.dumps(out, ensure_ascii=False)
    items = out.get("items") if isinstance(out, dict) else None
    while items and len(text) > MAX_TEXT:  # keep whole records: drop from the end until it fits
        items = items[: max(1, len(items) * 3 // 4)] if len(items) > 1 else []
        text = json.dumps(dict(out, items=items, shown=len(items), note="Shortened to fit; ask for fewer records."), ensure_ascii=False)
    return text


def tool_call(name, args):
    try:
        if name == "search_apis":
            res = json.dumps(search_apis(args.get("query", ""), args.get("limit", 10)), ensure_ascii=False)
        elif name == "describe_api":
            res = json.dumps(describe_api(args.get("api", "")), ensure_ascii=False)
        elif name == "call_api":
            res = call_api(args.get("api", ""), args.get("params") or {})
        else:
            raise ValueError(f"Unknown tool {name}")
        return {"content": [{"type": "text", "text": res}], "isError": False}
    except (ValueError, RuntimeError, OSError, KeyError) as e:
        return {"content": [{"type": "text", "text": str(e)}], "isError": True}


def handle(msg):
    m, p = msg.get("method"), msg.get("params") or {}
    if m == "initialize":
        v = p.get("protocolVersion")
        return {"protocolVersion": v if v in PROTOCOLS else PROTOCOLS[0], "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "pushbuild-mcp", "title": "Pushbuild Data APIs", "version": __version__},
                "instructions": "Public-data APIs from official sources. search_apis -> describe_api -> call_api."}
    if m == "ping":
        return {}
    if m == "tools/list":
        return {"tools": TOOLS}
    if m == "tools/call":
        return tool_call(p.get("name"), p.get("arguments") or {})
    raise LookupError(m)


def main():
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            out = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        else:
            if "id" not in msg:  # notification
                continue
            try:
                out = {"jsonrpc": "2.0", "id": msg["id"], "result": handle(msg)}
            except LookupError:
                out = {"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32601, "message": f"Method not found: {msg.get('method')}"}}
        sys.stdout.write(json.dumps(out) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
