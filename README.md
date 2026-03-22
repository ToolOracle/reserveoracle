# 🏦 reserveOracle

**Financial Data MCP Server** — 11 tools | Part of [ToolOracle](https://tooloracle.io)

![Tools](https://img.shields.io/badge/MCP_Tools-11-10B898?style=flat-square)
![Status](https://img.shields.io/badge/Status-Live-00C853?style=flat-square)
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
| `reserve_gold` | Live gold spot price (XAU) as a signed reserve evidence payload. Includes price, |
| `reserve_silver` | Live silver spot price (XAG) as a signed reserve evidence payload. Includes pric |
| `reserve_metals` | Live gold (XAU) and silver (XAG) prices in one call with signed evidence payload |
| `reserve_token_lookup` | Full RWA profile for any reserve asset token: PAXG, XAUT, BUIDL, USDC, USDT, EUR |
| `reserve_gold_tokens` | All gold-backed RWA tokens from the registry: PAXG (Paxos/Brinks), XAUT (Tether/ |
| `reserve_mica_assets` | All MiCA-relevant reserve assets from the RWA registry (80+ protocols). Filter b |
| `reserve_asset_types` | Browse all RWA asset types in the registry with token counts. Covers: stablecoin |
| `reserve_issuer` | Issuer deep-profile for any reserve token: legal name, LEI number, jurisdiction, |
| `reserve_snapshot` | Full signed reserve evidence snapshot for any asset. Combines live price data (f |
| `health_check` | ReserveOracle health status. |
| `reserve_token_context` | Token-level reserve context for any RWA token — the issuer-near view. Returns to |

## Pricing

| Tier | Rate Limit | Price |
|------|-----------|-------|
| Free | 100 calls/day | €0 |
| Pro | 10,000 calls/day | €29/month |
| Enterprise | Unlimited | Custom |

> Free tier includes all tools with rate limiting. Upgrade for higher limits and priority support.

## Part of ToolOracle

reserveOracle is one of **42 specialized MCP servers** in the [ToolOracle](https://tooloracle.io) ecosystem — the largest collection of production-ready MCP tools for AI agents.



**Related Oracles:**
- [FeedOracle](https://feedoracle.io) — Evidence-grade compliance data infrastructure
- [ToolOracle](https://tooloracle.io) — 42 Oracles, 390+ MCP Tools

## Links

- 🌐 Live: `https://tooloracle.io/reserve/mcp/`
- 📚 Docs: [tooloracle.io/docs](https://tooloracle.io/docs)
- 🏠 Platform: [tooloracle.io](https://tooloracle.io)

---

*Built by [FeedOracle](https://feedoracle.io) — Evidence by Design*
