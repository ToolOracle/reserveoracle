# 🏦 ReserveOracle

**Reserve Asset Intelligence MCP Server** — 10 tools | Part of [ToolOracle](https://tooloracle.io)

## Connect
```bash
npx -y mcp-remote https://tooloracle.io/reserve/mcp/
```

## What makes it different

Every tool returns a **signed evidence payload** — not just raw data:

```json
{
  "symbol": "XAU",
  "price_usd": 4713.2,
  "rwa_tokens": ["PAXG (Paxos/Brinks)", "XAUT (Tether/Swiss vault)"],
  "mica_relevance": "Reserve asset for gold-backed stablecoins — MiCA Art. 36",
  "asset_type": "commodity_reserve_asset",
  "evidence_type": "reserve_reference_snapshot",
  "content_hash": "sha256:c0345c0d4468a98d",
  "signed_at": "2026-03-19T09:38:07Z",
  "verify_url": "https://tooloracle.io/verify?asset=xau"
}
```

Three layers in one payload: **market data** + **RWA/token context** + **regulatory reference** + **cryptographic integrity**.

## Tools

| Tool | Credits | Description |
|------|---------|-------------|
| `reserve_gold` | 2u | Live XAU price as signed evidence payload (PAXG, XAUT context, MiCA Art.36) |
| `reserve_silver` | 2u | Live XAG price as signed evidence payload |
| `reserve_metals` | 2u | Gold + Silver + ratio in one signed call |
| `reserve_token_lookup` | 2u | Full RWA profile: PAXG, XAUT, BUIDL, USDC, RLUSD, EURC... |
| `reserve_gold_tokens` | 3u | All gold-backed RWA tokens + live XAU spot price |
| `reserve_mica_assets` | 3u | All MiCA-relevant assets, filter by type |
| `reserve_asset_types` | 1u | Browse 80+ protocols by asset type |
| `reserve_issuer` | 2u | Issuer deep-profile: LEI, regulator, custody |
| `reserve_snapshot` | 3u | Full signed reserve evidence snapshot (the enterprise payload) |
| `health_check` | free | Status |

## Example: reserve_snapshot for PAXG

```json
{
  "symbol": "PAXG",
  "asset_type": "commodity_gold",
  "live_underlying_price_usd": 4713.2,
  "custody": "Brinks",
  "lei": "549300BHQGE3I4ZVKW46",
  "mica_relevant": true,
  "content_hash": "sha256:735a0a97361a2ff4",
  "evidence_type": "reserve_reference_snapshot",
  "verify_url": "https://tooloracle.io/verify?asset=paxg"
}
```

## Example: reserve_issuer for BlackRock BUIDL

```json
{
  "token": "BUIDL",
  "issuer_name": "BlackRock, Inc.",
  "lei": "529900VBK42Y5HHRMD23",
  "regulator": ["SEC"],
  "custody": "Bank of New York Mellon",
  "min_investment": 5000000
}
```

## Registry Coverage

80+ protocols including:
- **Commodity gold**: PAXG, XAUT, XAUM (MatrixDock)
- **Stablecoins**: USDC, USDT, EURC, RLUSD, EURCV, EURe, PYUSD, USDP
- **Tokenized treasuries**: BUIDL (BlackRock), OUSG (Ondo), USTB (Superstate), USDY
- **EU-regulated**: Midas (BaFin), Societe Generale, Monerium, Spiko (AMF)
- **Money market funds**: WisdomTree, Sygnum, Figure Markets YLDS

## Pricing (1 unit = $0.01)

| Tier | Price | Units/Month |
|------|-------|-------------|
| Free | $0 | 50 |
| Starter | $49/mo | 500 |
| Pro | $149/mo | 2,000 |
| Agency | $349/mo | 6,000 |
| x402 | per call | unlimited |

## Part of ToolOracle

[tooloracle.io](https://tooloracle.io) — 12 products, 111 tools, all MCP-native.

## License

MIT
