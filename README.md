# 🏦 ReserveOracle

**Reserve Asset Intelligence MCP Server** — 11 tools | Part of [ToolOracle](https://tooloracle.io)

> Evidence payload format validated by ChatGPT, Gemini Pro, and Grok — March 2026

[![ReserveOracle MCP server](https://glama.ai/mcp/servers/ToolOracle/reserveoracle/badges/card.svg)](https://glama.ai/mcp/servers/ToolOracle/reserveoracle)

## Connect
```bash
npx -y mcp-remote https://tooloracle.io/reserve/mcp/
```

## What makes it different

Every tool returns a **combined evidence payload** with 4 layers simultaneously:

```json
{
  "asset": "gold",
  "symbol": "XAU",
  "asset_type": "commodity_reserve_asset",

  "price": 4709.4,
  "quote_currency": "USD",
  "unit": "USD/oz",
  "price_type": "spot",
  "market_status": "open",

  "market_data_source": "Yahoo Finance (GC=F / SI=F)",
  "reference_benchmark": "LBMA Gold Price PM",
  "backing_purity_standard": "London Good Delivery (LBMA)",
  "source_timestamp": "2026-03-19T09:58:44Z",
  "valid_until": "2026-03-20T09:58:44Z",

  "rwa_tokens": [
    { "symbol": "PAXG", "network": "ethereum", "contract": "0x45804880...", "issuer": "Paxos Trust Company" },
    { "symbol": "XAUT", "network": "ethereum", "contract": "0x68749665...", "issuer": "TG Commodities Limited" }
  ],

  "reserve_relevance": "Reference reserve asset for gold-backed token structures",
  "mica_relevance": "Reserve asset context for asset-referenced token analysis — MiCA Art. 36",
  "mica_context": {
    "classification_potential": "ART",
    "classification_basis": "commodity referenced",
    "title_reference": "MiCA Title IV"
  },
  "rank_context": { "reserve_rank": 1, "category": "commodity_reserve_asset" },

  "evidence_type": "reserve_reference_snapshot",
  "content_hash": "sha256:6910606724dd618d",
  "signature_alg": "ES256K",
  "signer_public_key": "0x0205705c9c2d2da037af7304164f7037e72b5fba8aae5ff6ff4e2ee848ada2f39f",
  "signature": "MEYCIQC9Uj-O4Rg00YGndqgA3SJc9BvSMrmvKv1RGlVnpArVxg...",
  "signed_at": "2026-03-19T09:58:44Z",
  "verify_url": "https://tooloracle.io/verify/reserve/fo-d029bcb238d4"
}
```

### 4 layers in one payload

| Layer | Fields |
|-------|--------|
| **API cleanness** | `price`, `quote_currency`, `market_status`, `rwa_tokens` as objects |
| **Verifiability** | `signature`, `signer_public_key`, `content_hash`, `verify_url` |
| **Evidence snapshot** | `source_timestamp`, `valid_until`, `evidence_type`, `reference_benchmark` |
| **ReserveOracle differentiation** | `reserve_relevance`, `mica_relevance`, `mica_context`, `rank_context` |

### Two payload types — cleanly separated

| | Asset-Level | Token-Level |
|--|-------------|-------------|
| Tool | `reserve_gold`, `reserve_silver` | `reserve_token_context` |
| Focus | Gold/Silver as reserve asset | PAXG/XAUT/BUIDL issuer + structure |
| `evidence_type` | `reserve_reference_snapshot` | `token_reserve_context` |
| Includes | Live price, LBMA benchmark, rwa_tokens | Custody, LEI, vault location, audit frequency |

## Tools

| Tool | Credits | Description |
|------|---------|-------------|
| `reserve_gold` | 2u | Live XAU — full combined evidence payload |
| `reserve_silver` | 2u | Live XAG — full combined evidence payload |
| `reserve_metals` | 2u | Gold + Silver + ratio in one signed call |
| `reserve_token_lookup` | 2u | Full RWA profile: PAXG, XAUT, BUIDL, USDC, RLUSD... |
| `reserve_gold_tokens` | 3u | All gold-backed RWA tokens + live XAU spot |
| `reserve_mica_assets` | 3u | All MiCA-relevant assets, filter by type |
| `reserve_asset_types` | 1u | Browse 80+ protocols by asset type |
| `reserve_issuer` | 2u | Issuer deep-profile: LEI, regulator, custody |
| `reserve_snapshot` | 3u | Full reserve evidence snapshot |
| `reserve_token_context` | 2u | Token-level: custody, vault location, audit frequency, regulatory status |
| `health_check` | free | Status |

## PAXG vs XAUT — instant risk differentiation

```json
PAXG: vault_location=London, audit=monthly, regulatory_status=["NYDFS regulated", "qualified custodian"], lei="549300BHQGE3I4ZVKW46"
XAUT: vault_location=Switzerland, audit=quarterly, regulatory_status=["BVI registered", "unregulated issuer"], lei=null
```

## Cryptographic verification

- Algorithm: **ES256K** (secp256k1) — same as Ethereum
- Public key: `0x0205705c9c2d2da037af7304164f7037e72b5fba8aae5ff6ff4e2ee848ada2f39f`
- JWKS: `https://feedoracle.io/.well-known/jwks.json`
- Every payload: `content_hash` + real `signature` + `verify_url` with request ID

## Registry Coverage

80+ protocols including gold tokens, stablecoins, tokenized treasuries, money market funds.
PAXG, XAUT, BUIDL (BlackRock), OUSG (Ondo), USDC, USDT, EURC, RLUSD, EURCV, EURe, Midas (BaFin), Spiko (AMF).

## Pricing

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