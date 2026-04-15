# 🏦 ReserveOracle

**Reserve Asset Intelligence MCP Server** — 11 tools | Part of [ToolOracle](https://tooloracle.io)

![Tools](https://img.shields.io/badge/MCP_Tools-11-10B898?style=flat-square)
![Status](https://img.shields.io/badge/Status-Live-00C853?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)
![Tier](https://img.shields.io/badge/Tier-Free-2196F3?style=flat-square)

## Quick Connect

```bash
# Claude Desktop / Cursor / Windsurf
npx -y mcp-remote https://tooloracle.io/reserve/mcp/
```

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "reserveoracle": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://tooloracle.io/reserve/mcp/"]
    }
  }
}
```

## Tools (11)

| Tool | Description |
|------|-------------|
| `reserve_gold` | Live gold spot price (XAU) with signed evidence payload |
| `reserve_silver` | Live silver spot price (XAG) with signed evidence payload |
| `reserve_metals` | Gold + silver prices in one call with signed evidence |
| `reserve_token_lookup` | Full RWA profile for any reserve asset token (PAXG, XAUT, BUIDL, etc.) |
| `reserve_gold_tokens` | All gold-backed RWA tokens from the registry |
| `reserve_mica_assets` | MiCA-relevant reserve assets from 80+ RWA protocols |
| `reserve_asset_types` | Browse all RWA asset types with token counts |
| `reserve_issuer` | Issuer deep-profile: legal name, LEI, jurisdiction, custody |
| `reserve_snapshot` | Full signed reserve evidence snapshot for any asset |
| `reserve_token_context` | Token-level reserve context — issuer-near view |
| `health_check` | Service health status |

## Pricing

| Tier | Rate Limit | Price |
|------|-----------|-------|
| Free | 100 calls/day | $0 |
| Pro | 1,100 units/month | $49/month |
| Agent | 5,500 units/month | $299/month |
| x402 | Pay per call | $0.01/call USDC on Base |

> Free tier includes all tools with rate limiting. Register with `kya_register` for 500 welcome units.

## Part of ToolOracle

ReserveOracle is one of **100+ MCP servers** in the [ToolOracle](https://tooloracle.io) ecosystem — self-serve MCP infrastructure for AI agents with 1,200+ tools across 8 categories.

## Links

- 🌐 Live: `https://tooloracle.io/reserve/mcp/`
- 📚 Docs: [tooloracle.io/docs](https://tooloracle.io/docs)
- 🏠 Platform: [tooloracle.io](https://tooloracle.io)

---

*Built by [FeedOracle Technologies](https://feedoracle.io) — Evidence by Design*
