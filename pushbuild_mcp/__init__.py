"""Local stdio MCP server for the Pushbuild data APIs: relays each JSON-RPC message to https://api.pushbuild.com/mcp with your API key."""
import json, os, sys, urllib.error, urllib.request

URL = os.environ.get("PUSHBUILD_MCP_URL", "https://api.pushbuild.com/mcp")
__version__ = "0.1.0"


def relay(msg, key, session):
    h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "User-Agent": f"pushbuild-mcp/{__version__}"}
    if key:
        h["X-API-Key"] = key
    if session[0]:
        h["Mcp-Session-Id"] = session[0]
    req = urllib.request.Request(URL, data=json.dumps(msg).encode(), headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            session[0] = r.headers.get("Mcp-Session-Id") or session[0]
            body = r.read().decode()
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if e.code == 401:
            return {"jsonrpc": "2.0", "id": msg.get("id"), "error": {"code": -32001, "message": "Set PUSHBUILD_API_KEY (free key: https://pushbuild.com/apis/app/signup)"}}
        if not body.strip().startswith("{"):
            return {"jsonrpc": "2.0", "id": msg.get("id"), "error": {"code": -32000, "message": f"HTTP {e.code}"}}
    except OSError as e:
        return {"jsonrpc": "2.0", "id": msg.get("id"), "error": {"code": -32000, "message": str(e)}}
    if not body.strip():
        return None
    if body.lstrip().startswith("data:") or "\ndata:" in body:  # event-stream reply: take the last data line
        body = [l[5:].strip() for l in body.splitlines() if l.startswith("data:")][-1]
    return json.loads(body)


def main():
    key, session = os.environ.get("PUSHBUILD_API_KEY", ""), [None]
    for line in sys.stdin:
        if not line.strip():
            continue
        msg = json.loads(line)
        out = relay(msg, key, session)
        if out is not None and "id" in msg:
            sys.stdout.write(json.dumps(out) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
