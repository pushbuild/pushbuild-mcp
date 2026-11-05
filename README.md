# pushbuild-mcp

A local (stdio) MCP server for the Pushbuild data APIs: 400+ official public-data sources, each returning clean JSON records with a stated source. Coverage includes US election results and campaign finance, lobbying, court cases, restaurant inspections, building permits, business registries, SEC filings and 13F holdings, recalls, sanctions lists, central bank and economic statistics, and weather.

It runs on your machine and needs nothing beyond Python 3.9+. Search runs locally over the public catalog (https://api.pushbuild.com/llms.txt), describe reads each API's OpenAPI spec, and call_api runs the API through the Pushbuild REST API with your key.

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
