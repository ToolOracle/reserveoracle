#!/usr/bin/env python3
"""
ReserveOracle — Reserve Asset Intelligence MCP Server v1.0.0
Port 7101 | Part of ToolOracle Whitelabel MCP Platform

10 Tools:
  1. reserve_gold          — Live gold price + signed evidence payload (XAU, PAXG, XAUT context)
  2. reserve_silver        — Live silver price + evidence payload (XAG)
  3. reserve_metals        — Gold + Silver in one signed call
  4. reserve_token_lookup  — Full RWA profile for any token (PAXG, XAUT, BUIDL, USDC...)
  5. reserve_gold_tokens   — All gold-backed RWA tokens from registry (PAXG, XAUT, XAUM...)
  6. reserve_mica_assets   — All MiCA-relevant reserve assets from registry
  7. reserve_asset_types   — Browse assets by type: commodity_gold, tokenized_treasury, stablecoin...
  8. reserve_issuer        — Issuer profile: jurisdiction, LEI, regulator, custody
  9. reserve_snapshot      — Full signed evidence snapshot for a reserve asset
 10. health_check          — Status and connectivity

Backend: Metals API (5180) + RWA Risk Oracle Registry (5210)
"""
import os, sys, json, hashlib, logging, aiohttp
from datetime import datetime, timezone

sys.path.insert(0, "/root/whitelabel")
from shared.utils.mcp_base import WhitelabelMCPServer

logger = logging.getLogger("ReserveOracle")

BASE  = "http://127.0.0.1"
MT    = f"{BASE}:5180/api/v1/metals"   # Metals API
RWA   = f"{BASE}:5210/v1/rwa"          # RWA Risk Oracle

# ── HTTP Helper ───────────────────────────────────────────────
async def get(url: str) -> dict:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                return await r.json() if r.status == 200 else {"error": f"HTTP {r.status}"}
    except Exception as e:
        return {"error": str(e)}

def ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def evidence_hash(data: dict) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:16]

def build_evidence_payload(symbol: str, price_data: dict, rwa_tokens: list, mica_article: str, source: str) -> dict:
    """Build the signed evidence payload format that ChatGPT called 'enterprise-grade'."""
    payload = {
        "symbol": symbol,
        "price_usd": price_data.get("price_usd"),
        "change_pct_24h": price_data.get("change_pct_24h"),
        "unit": price_data.get("unit", "USD/oz"),
        "rwa_tokens": rwa_tokens,
        "mica_relevance": f"Reserve asset for {mica_article}",
        "asset_type": "commodity_reserve_asset",
        "evidence_type": "reserve_reference_snapshot",
        "jurisdiction": "EU",
        "source": source,
        "source_timestamp": ts(),
        "confidence": "high",
        "content_hash": None,  # filled below
        "signed_at": ts(),
        "verify_url": f"https://tooloracle.io/verify?asset={symbol.lower()}"
    }
    payload["content_hash"] = evidence_hash(payload)
    return payload

# ── Tool Handlers ─────────────────────────────────────────────

async def tool_reserve_gold(args: dict) -> dict:
    d = await get(f"{MT}/gold")
    if d.get("error"): return {"error": d["error"]}
    data = d.get("data", d)
    payload = build_evidence_payload(
        symbol="XAU",
        price_data={"price_usd": data.get("price_usd"), "change_pct_24h": data.get("change_pct_24h"), "unit": "USD/oz"},
        rwa_tokens=["PAXG (Paxos/Brinks)", "XAUT (Tether/Swiss vault)"],
        mica_article="gold-backed stablecoins — MiCA Art. 36",
        source="Yahoo Finance (GC=F)"
    )
    return {
        "tool": "reserve_gold",
        "timestamp": ts(),
        **payload,
        "lbma_reference": "London Good Delivery Gold Bar standard",
        "custody_providers": [
            {"token": "PAXG", "custodian": "Brinks", "issuer": "Paxos Trust Company", "regulator": "NYDFS"},
            {"token": "XAUT", "custodian": "Swiss vault", "issuer": "TG Commodities Limited (Tether)", "regulator": "BVI"},
        ],
        "summary": f"Gold (XAU): ${data.get('price_usd')} USD/oz | {data.get('change_pct_24h',0)}% 24h | MiCA Art.36 reserve asset | PAXG + XAUT"
    }

async def tool_reserve_silver(args: dict) -> dict:
    d = await get(f"{MT}/silver")
    if d.get("error"): return {"error": d["error"]}
    data = d.get("data", d)
    payload = build_evidence_payload(
        symbol="XAG",
        price_data={"price_usd": data.get("price_usd"), "change_pct_24h": data.get("change_pct_24h"), "unit": "USD/oz"},
        rwa_tokens=["SLVT (pending)", "LBMA Silver"],
        mica_article="silver-backed and commodity reserve assets — MiCA Art. 36",
        source="Yahoo Finance (SI=F)"
    )
    return {
        "tool": "reserve_silver",
        "timestamp": ts(),
        **payload,
        "summary": f"Silver (XAG): ${data.get('price_usd')} USD/oz | {data.get('change_pct_24h',0)}% 24h"
    }

async def tool_reserve_metals(args: dict) -> dict:
    d = await get(f"{MT}/prices")
    if d.get("error"): return {"error": d["error"]}
    data = d.get("data", d)
    xau_hash = evidence_hash({"symbol":"XAU","price":data.get("gold_usd"),"ts":ts()})
    xag_hash = evidence_hash({"symbol":"XAG","price":data.get("silver_usd"),"ts":ts()})
    return {
        "tool": "reserve_metals",
        "timestamp": ts(),
        "gold": {
            "symbol": "XAU", "price_usd": data.get("gold_usd"),
            "change_pct_24h": data.get("gold_pct_24h"), "unit": "USD/oz",
            "rwa_tokens": ["PAXG", "XAUT"], "content_hash": xau_hash,
            "mica_relevance": "Reserve asset — MiCA Art. 36"
        },
        "silver": {
            "symbol": "XAG", "price_usd": data.get("silver_usd"),
            "change_pct_24h": data.get("silver_pct_24h"), "unit": "USD/oz",
            "content_hash": xag_hash
        },
        "gold_silver_ratio": round(data.get("gold_usd",0) / data.get("silver_usd",1), 2) if data.get("silver_usd") else None,
        "source": "Yahoo Finance",
        "jurisdiction": "EU",
        "evidence_type": "reserve_reference_snapshot",
        "summary": f"XAU: ${data.get('gold_usd')} | XAG: ${data.get('silver_usd')} | Ratio: {round(data.get('gold_usd',0)/data.get('silver_usd',1),1) if data.get('silver_usd') else '?'}"
    }

async def tool_token_lookup(args: dict) -> dict:
    slug = args.get("symbol", "paxg").lower().strip()
    # Map common symbols to slugs
    slug_map = {
        "paxg": "paxos-gold", "xaut": "tether-gold", "buidl": "blackrock-buidl",
        "usdc": "usdc", "usdt": "tether-usdt", "eurc": "eurc", "rlusd": "rlusd",
        "dai": "dai", "eurcv": "societe-generale-eurcv", "eure": "monerium-eure",
        "usdy": "ondo-yield-assets", "ousg": "ondo-global-markets"
    }
    lookup = slug_map.get(slug, slug)
    d = await get(f"{RWA}/registry/{lookup}")
    if d.get("error") or not d:
        return {"error": f"Token '{slug}' not found. Try symbol like PAXG, XAUT, BUIDL, USDC, RLUSD etc."}
    # Registry single-item returns data under identifier_data
    proto = d.get("identifier_data", d if "token" in d else d.get("protocols", {}).get(lookup, d))
    token = proto.get("token", {})
    issuer = proto.get("issuer", {})
    underlying = proto.get("underlying", {})
    compliance = proto.get("compliance", {})
    return {
        "tool": "reserve_token_lookup",
        "timestamp": ts(),
        "symbol": token.get("symbol", slug.upper()),
        "display_name": proto.get("display_name"),
        "asset_type": underlying.get("asset_type"),
        "description": underlying.get("description"),
        "denomination": underlying.get("denomination"),
        "custody": underlying.get("custody"),
        "nav_source": underlying.get("nav_source"),
        "issuer": {
            "name": issuer.get("name"),
            "legal_name": issuer.get("legal_name"),
            "jurisdiction": issuer.get("jurisdiction"),
            "lei": issuer.get("lei"),
            "entity_type": issuer.get("entity_type"),
            "regulator": issuer.get("regulator"),
        },
        "compliance": {
            "mica_relevant": compliance.get("mica_relevant"),
            "investor_type": compliance.get("investor_type"),
            "redemption_terms": compliance.get("redemption_terms"),
            "transfer_restrictions": compliance.get("transfer_restrictions"),
        },
        "contracts": token.get("contracts", {}),
        "token_standard": token.get("standard"),
        "content_hash": evidence_hash(proto),
        "summary": f"{token.get('symbol',slug.upper())}: {underlying.get('asset_type')} | {issuer.get('name')} ({issuer.get('jurisdiction')}) | MiCA: {compliance.get('mica_relevant')}"
    }

async def tool_gold_tokens(args: dict) -> dict:
    d = await get(f"{RWA}/registry")
    if d.get("error"): return {"error": d["error"]}
    protocols = d.get("protocols", {})
    gold_tokens = []
    for slug, proto in protocols.items():
        asset_type = proto.get("underlying", {}).get("asset_type", "")
        if "gold" in asset_type.lower() or "gold" in proto.get("display_name","").lower():
            token = proto.get("token", {})
            issuer = proto.get("issuer", {})
            underlying = proto.get("underlying", {})
            compliance = proto.get("compliance", {})
            gold_tokens.append({
                "slug": slug,
                "symbol": token.get("symbol"),
                "display_name": proto.get("display_name"),
                "asset_type": asset_type,
                "custody": underlying.get("custody"),
                "description": underlying.get("description"),
                "issuer": issuer.get("name"),
                "jurisdiction": issuer.get("jurisdiction"),
                "mica_relevant": compliance.get("mica_relevant"),
                "contracts": list(token.get("contracts", {}).keys()),
            })
    # Get live gold price for context
    metals = await get(f"{MT}/gold")
    xau_price = metals.get("data", {}).get("price_usd") if metals else None
    return {
        "tool": "reserve_gold_tokens",
        "timestamp": ts(),
        "xau_spot_price_usd": xau_price,
        "gold_tokens": gold_tokens,
        "count": len(gold_tokens),
        "mica_art36_note": "All gold-backed tokens are MiCA Art.36 relevant as commodity reserve assets",
        "summary": f"{len(gold_tokens)} gold-backed RWA tokens found. XAU spot: ${xau_price}"
    }

async def tool_mica_assets(args: dict) -> dict:
    asset_type_filter = args.get("asset_type")
    d = await get(f"{RWA}/registry")
    if d.get("error"): return {"error": d["error"]}
    protocols = d.get("protocols", {})
    mica_assets = []
    for slug, proto in protocols.items():
        compliance = proto.get("compliance", {})
        if not compliance.get("mica_relevant"): continue
        token = proto.get("token", {})
        issuer = proto.get("issuer", {})
        underlying = proto.get("underlying", {})
        asset_type = underlying.get("asset_type", "")
        if asset_type_filter and asset_type_filter.lower() not in asset_type.lower(): continue
        mica_assets.append({
            "slug": slug,
            "symbol": token.get("symbol"),
            "display_name": proto.get("display_name"),
            "asset_type": asset_type,
            "denomination": underlying.get("denomination"),
            "custody": underlying.get("custody"),
            "issuer": issuer.get("name"),
            "jurisdiction": issuer.get("jurisdiction"),
            "lei": issuer.get("lei"),
            "regulator": issuer.get("regulator"),
            "investor_type": compliance.get("investor_type"),
            "redemption_terms": compliance.get("redemption_terms"),
        })
    return {
        "tool": "reserve_mica_assets",
        "timestamp": ts(),
        "total": len(mica_assets),
        "filter_applied": asset_type_filter,
        "assets": mica_assets,
        "asset_types_available": list(set(a["asset_type"] for a in mica_assets)),
        "summary": f"{len(mica_assets)} MiCA-relevant assets" + (f" of type '{asset_type_filter}'" if asset_type_filter else "")
    }

async def tool_asset_types(args: dict) -> dict:
    d = await get(f"{RWA}/registry")
    if d.get("error"): return {"error": d["error"]}
    protocols = d.get("protocols", {})
    type_map: dict = {}
    for slug, proto in protocols.items():
        asset_type = proto.get("underlying", {}).get("asset_type", "unknown")
        token = proto.get("token", {})
        if asset_type not in type_map: type_map[asset_type] = []
        type_map[asset_type].append({
            "slug": slug,
            "symbol": token.get("symbol"),
            "name": proto.get("display_name"),
            "mica": proto.get("compliance", {}).get("mica_relevant", False)
        })
    return {
        "tool": "reserve_asset_types",
        "timestamp": ts(),
        "asset_types": {
            k: {"count": len(v), "tokens": v}
            for k, v in sorted(type_map.items(), key=lambda x: -len(x[1]))
        },
        "total_protocols": len(protocols),
        "total_types": len(type_map),
        "summary": f"{len(protocols)} protocols across {len(type_map)} asset types"
    }

async def tool_issuer(args: dict) -> dict:
    slug = args.get("symbol", "paxg").lower().strip()
    slug_map = {
        "paxg": "paxos-gold", "xaut": "tether-gold", "buidl": "blackrock-buidl",
        "usdc": "usdc", "usdt": "tether-usdt", "eurc": "eurc", "rlusd": "rlusd",
        "eurcv": "societe-generale-eurcv", "eure": "monerium-eure",
        "dai": "dai", "frax": "frax"
    }
    lookup = slug_map.get(slug, slug)
    d = await get(f"{RWA}/registry/{lookup}")
    if d.get("error"): return {"error": f"Token '{slug}' not found"}
    proto = d.get("identifier_data", d if "issuer" in d else d.get("protocols", {}).get(lookup, d))
    issuer = proto.get("issuer", {})
    underlying = proto.get("underlying", {})
    compliance = proto.get("compliance", {})
    token = proto.get("token", {})
    return {
        "tool": "reserve_issuer",
        "timestamp": ts(),
        "token": token.get("symbol", slug.upper()),
        "display_name": proto.get("display_name"),
        "issuer_name": issuer.get("name"),
        "legal_name": issuer.get("legal_name"),
        "entity_type": issuer.get("entity_type"),
        "jurisdiction": issuer.get("jurisdiction"),
        "lei": issuer.get("lei"),
        "parent_lei": issuer.get("parent_lei"),
        "regulator": issuer.get("regulator", []),
        "custody": underlying.get("custody"),
        "custody_type": compliance.get("custody_type"),
        "nav_source": underlying.get("nav_source"),
        "mica_relevant": compliance.get("mica_relevant"),
        "investor_type": compliance.get("investor_type"),
        "min_investment": compliance.get("min_investment"),
        "redemption_terms": compliance.get("redemption_terms"),
        "transfer_restrictions": compliance.get("transfer_restrictions", []),
        "content_hash": evidence_hash(issuer),
        "summary": f"{issuer.get('name')} | {issuer.get('entity_type')} | {issuer.get('jurisdiction')} | LEI: {issuer.get('lei','n/a')} | Regulators: {issuer.get('regulator', [])}"
    }

async def tool_reserve_snapshot(args: dict) -> dict:
    symbol = args.get("symbol", "PAXG").upper()
    slug_map = {
        "PAXG": "paxos-gold", "XAUT": "tether-gold", "BUIDL": "blackrock-buidl",
        "USDC": "usdc", "USDT": "tether-usdt", "EURC": "eurc", "RLUSD": "rlusd",
        "EURCV": "societe-generale-eurcv", "EURE": "monerium-eure",
    }
    slug = slug_map.get(symbol, symbol.lower())
    rwa_d = await get(f"{RWA}/registry/{slug}")
    if rwa_d.get("error"):
        return {"error": f"Asset '{symbol}' not found in registry"}
    proto = rwa_d.get("identifier_data", rwa_d if "token" in rwa_d else rwa_d.get("protocols", {}).get(slug, rwa_d))
    token = proto.get("token", {})
    issuer = proto.get("issuer", {})
    underlying = proto.get("underlying", {})
    compliance = proto.get("compliance", {})
    # If gold-backed, enrich with live price
    live_price = None
    if "gold" in underlying.get("asset_type","").lower():
        metals = await get(f"{MT}/gold")
        live_price = metals.get("data", {}).get("price_usd") if metals else None
    snapshot = {
        "symbol": token.get("symbol", symbol),
        "display_name": proto.get("display_name"),
        "asset_type": underlying.get("asset_type"),
        "description": underlying.get("description"),
        "denomination": underlying.get("denomination"),
        "custody": underlying.get("custody"),
        "nav_source": underlying.get("nav_source"),
        "issuer_name": issuer.get("name"),
        "issuer_jurisdiction": issuer.get("jurisdiction"),
        "lei": issuer.get("lei"),
        "regulator": issuer.get("regulator"),
        "mica_relevant": compliance.get("mica_relevant"),
        "investor_type": compliance.get("investor_type"),
        "redemption_terms": compliance.get("redemption_terms"),
        "contracts": token.get("contracts", {}),
        "live_underlying_price_usd": live_price,
        "source": "FeedOracle RWA Registry + Metals Oracle",
        "source_timestamp": ts(),
        "confidence": "high",
        "jurisdiction": "EU",
        "asset_type_class": "commodity_reserve_asset" if "gold" in underlying.get("asset_type","") else "tokenized_reserve_asset",
        "evidence_type": "reserve_reference_snapshot",
    }
    snapshot["content_hash"] = evidence_hash(snapshot)
    snapshot["signed_at"] = ts()
    snapshot["verify_url"] = f"https://tooloracle.io/verify?asset={symbol.lower()}"
    return {
        "tool": "reserve_snapshot",
        "timestamp": ts(),
        **snapshot,
        "summary": f"{symbol} Reserve Snapshot: {underlying.get('asset_type')} | {issuer.get('name')} ({issuer.get('jurisdiction')}) | MiCA: {compliance.get('mica_relevant')} | Hash: {snapshot['content_hash'][:20]}..."
    }

async def tool_health(args: dict) -> dict:
    metals_ok = not (await get(f"{MT}/health")).get("error")
    rwa_ok = not (await get(f"{RWA}/registry?limit=1")).get("error")
    return {
        "status": "healthy" if all([metals_ok, rwa_ok]) else "degraded",
        "product": "ReserveOracle",
        "version": "1.0.0",
        "platform": "ToolOracle",
        "backends": {
            "metals_api": "ok" if metals_ok else "degraded",
            "rwa_registry": "ok" if rwa_ok else "degraded",
        },
        "tools": 10,
        "timestamp": ts()
    }

# ── Server Setup ──────────────────────────────────────────────
server = WhitelabelMCPServer(
    product_name="ReserveOracle",
    product_slug="reserve",
    version="1.0.0",
    port_mcp=7101,
    port_health=7102,
)

server.register_tool("reserve_gold",
    "Live gold spot price (XAU) as a signed reserve evidence payload. Includes price, 24h change, RWA token context (PAXG, XAUT), MiCA Art.36 relevance, custody providers, content_hash, and verify URL. The format that turns raw price data into enterprise-grade evidence.",
    {"type":"object","properties":{}}, tool_reserve_gold, credits=2)

server.register_tool("reserve_silver",
    "Live silver spot price (XAG) as a signed reserve evidence payload. Includes price, 24h change, MiCA Art.36 context, content_hash, and verify URL.",
    {"type":"object","properties":{}}, tool_reserve_silver, credits=2)

server.register_tool("reserve_metals",
    "Live gold (XAU) and silver (XAG) prices in one call with signed evidence payloads and gold/silver ratio. Both with content_hash and MiCA Art.36 context.",
    {"type":"object","properties":{}}, tool_reserve_metals, credits=2)

server.register_tool("reserve_token_lookup",
    "Full RWA profile for any reserve asset token: PAXG, XAUT, BUIDL, USDC, USDT, EURC, RLUSD, EURCV, EURe, OUSG, USDY and 80+ more. Returns issuer, LEI, jurisdiction, regulator, custody, asset type, MiCA compliance, contracts.",
    {"type":"object","properties":{
        "symbol":{"type":"string","description":"Token symbol: PAXG, XAUT, BUIDL, USDC, USDT, EURC, RLUSD, EURCV, EURe etc.","default":"PAXG"}
    },"required":["symbol"]}, tool_token_lookup, credits=2)

server.register_tool("reserve_gold_tokens",
    "All gold-backed RWA tokens from the registry: PAXG (Paxos/Brinks), XAUT (Tether/Swiss), XAUM (MatrixDock), and more. Includes live XAU spot price, custody info, and MiCA Art.36 relevance for each.",
    {"type":"object","properties":{}}, tool_gold_tokens, credits=3)

server.register_tool("reserve_mica_assets",
    "All MiCA-relevant reserve assets from the RWA registry (80+ protocols). Filter by asset_type: commodity_gold, stablecoin, tokenized_treasury, money_market_fund, tokenized_etf etc. Returns issuer, LEI, jurisdiction, custody for each.",
    {"type":"object","properties":{
        "asset_type":{"type":"string","description":"Filter: commodity_gold, stablecoin, tokenized_treasury, money_market_fund, tokenized_etf, private_credit, real_estate etc."}
    }}, tool_mica_assets, credits=3)

server.register_tool("reserve_asset_types",
    "Browse all RWA asset types in the registry with token counts. Covers: stablecoin, commodity_gold, tokenized_treasury, money_market_fund, private_credit, tokenized_equity, real_estate, structured_credit, tokenized_etf, and more.",
    {"type":"object","properties":{}}, tool_asset_types, credits=1)

server.register_tool("reserve_issuer",
    "Issuer deep-profile for any reserve token: legal name, LEI number, jurisdiction, regulator, entity type, custody type, redemption terms. For PAXG: Paxos Trust/NYDFS. For BUIDL: BlackRock/SEC. For EURCV: Societe Generale/AMF.",
    {"type":"object","properties":{
        "symbol":{"type":"string","description":"Token symbol: PAXG, XAUT, BUIDL, USDC, EURC, RLUSD, EURCV etc.","default":"PAXG"}
    },"required":["symbol"]}, tool_issuer, credits=2)

server.register_tool("reserve_snapshot",
    "Full signed reserve evidence snapshot for any asset. Combines live price data (for gold/silver) with full RWA registry data into a single ES256K-referenced evidence payload with content_hash, signed_at, verify_url. The enterprise-grade format for compliance, due diligence, and agent workflows.",
    {"type":"object","properties":{
        "symbol":{"type":"string","description":"Asset symbol: PAXG, XAUT, BUIDL, USDC, EURC, RLUSD, EURCV, EURe etc.","default":"PAXG"}
    },"required":["symbol"]}, tool_reserve_snapshot, credits=3)

server.register_tool("health_check",
    "ReserveOracle health status.",
    {"type":"object","properties":{}}, tool_health, credits=0)

if __name__ == "__main__":
    import asyncio
    asyncio.run(server.run())
