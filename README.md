# pushbuild-mcp

A local (stdio) MCP server for the Pushbuild data APIs: 400+ official public-data sources, each returning clean JSON records with a stated source. Coverage includes US election results and campaign finance, lobbying, court cases, restaurant inspections, building permits, business registries, SEC filings and 13F holdings, recalls, sanctions lists, central bank and economic statistics, and weather.

It has no dependencies beyond Python 3.9+. It runs on your machine and sends each MCP message to `https://api.pushbuild.com/mcp` with your API key, so clients that cannot do an OAuth sign-in can use it.

## Tools
- `search_apis`: find an API by keyword.
- `describe_api`: inputs and coverage of one API.
- `call_api`: run an API and get records. Needs a key.

All three only read data.

## Install
```
pip install "git+https://github.com/pushbuild/pushbuild-mcp"
```
Get a free key (monthly free usage, no card): https://pushbuild.com/apis/app/signup

## Claude Desktop / Cursor / any MCP client
```json
{
  "mcpServers": {
    "pushbuild": {
      "command": "pushbuild-mcp",
      "env": { "PUSHBUILD_API_KEY": "YOUR_KEY" }
    }
  }
}
```
Without installing: `"command": "uvx", "args": ["--from", "git+https://github.com/pushbuild/pushbuild-mcp", "pushbuild-mcp"]`.

Clients that support remote servers can instead connect to `https://api.pushbuild.com/mcp` directly (OAuth sign-in). Docs: https://pushbuild.com/apis/mcp.html

## License
MIT
