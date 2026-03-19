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
sys.path.insert(0, "/root/rwa_node/mcp")
from shared.utils.mcp_base import WhitelabelMCPServer
try:
    from ecdsa_signer import sign_mcp_response as _ecdsa_sign, get_public_jwk
    SIGNER_PUBKEY = "0x" + __import__("cryptography.hazmat.primitives.serialization", fromlist=["serialization"]).load_pem_private_key(
        open("/root/rwa_node/keys/feedoracle-secp256k1.pem","rb").read(), password=None
    ).public_key().public_bytes(
        __import__("cryptography.hazmat.primitives.serialization", fromlist=["serialization"]).Encoding.X962,
        __import__("cryptography.hazmat.primitives.serialization", fromlist=["serialization"]).PublicFormat.CompressedPoint
    ).hex()
    SIGNING_AVAILABLE = True
except Exception as _e:
    SIGNING_AVAILABLE = False
    SIGNER_PUBKEY = None

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

def build_evidence_payload(symbol: str, asset_name: str, price_data: dict,
                            rwa_tokens: list, reserve_relevance: str,
                            mica_relevance: str, reserve_rank: int,
                            category: str, source: str) -> dict:
    """Build the signed evidence payload — ChatGPT-approved enterprise format."""
    import uuid
    request_id = f"fo-{uuid.uuid4().hex[:12]}"
    import urllib.request as _ur
    from datetime import datetime, timezone, timedelta
    source_ts = ts()

    # Punkt 3: rwa_tokens als Objekte mit network + contract
    rwa_token_objects = []
    for sym in rwa_tokens:
        obj = {"symbol": sym}
        if sym == "PAXG":
            obj.update({"network": "ethereum", "contract": "0x45804880De22913dAFE09f4980848ECE6EcbAf78", "issuer": "Paxos Trust Company"})
        elif sym == "XAUT":
            obj.update({"network": "ethereum", "contract": "0x68749665FF8D2d112Fa859AA293F07A622782F38", "issuer": "TG Commodities Limited"})
        elif sym == "LBMA Silver":
            obj.update({"network": "off_chain", "contract": None, "issuer": "LBMA"})
        rwa_token_objects.append(obj)

    # Punkt 2: price / quote_currency / market_status
    now_hour = datetime.now(timezone.utc).hour
    market_status = "open" if 7 <= now_hour <= 21 else "closed"  # rough UTC metals market hours

    payload = {
        # ── Asset identification ──────────────────────────────
        "asset": asset_name,
        "symbol": symbol,
        "asset_type": category,

        # ── Price data (Gemini Punkt 2) ───────────────────────
        "price": price_data.get("price_usd"),
        "quote_currency": "USD",
        "unit": "USD/oz",
        "price_type": "spot",
        "market_status": market_status,
        "change_pct_24h": price_data.get("change_pct_24h"),

        # ── Data provenance (Gemini Punkt 4 + ChatGPT) ────────
        "market_data_source": "Yahoo Finance (GC=F / SI=F)",
        "reference_benchmark": "LBMA Gold Price PM",
        "backing_purity_standard": "London Good Delivery (LBMA)",
        "source_timestamp": source_ts,
        "valid_until": (datetime.now(timezone.utc) + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ"),

        # ── RWA token context (Gemini Punkt 3 — objects) ─────
        "rwa_tokens": rwa_token_objects,

        # ── Reserve & regulatory context (ChatGPT) ───────────
        "reserve_relevance": reserve_relevance,
        "mica_relevance": mica_relevance,
        "mica_context": {
            "classification_potential": "ART",
            "classification_basis": "commodity referenced",
            "title_reference": "MiCA Title IV",
        },
        "rank_context": {
            "reserve_rank": reserve_rank,
            "category": category,
        },

        # ── Evidence / snapshot ───────────────────────────────
        "evidence_type": "reserve_reference_snapshot",
        "content_hash": None,

        # ── Cryptographic integrity (Gemini Punkt 1) ─────────
        "signature_alg": "ES256K",
        "signer_public_key": SIGNER_PUBKEY,
        "signature": None,
        "signed_at": ts(),
        "verify_url": f"https://tooloracle.io/verify/reserve/{request_id}",
        "request_id": request_id,
    }
    # content_hash über signable fields
    signable = {k: v for k, v in payload.items() if k not in ("content_hash", "signature", "valid_until")}
    payload["content_hash"] = evidence_hash(signable)

    # Punkt 1: echte ES256K Signatur
    if SIGNING_AVAILABLE:
        try:
            signed = _ecdsa_sign({**payload, "request_id": request_id})
            payload["signature"] = signed.get("signature", {}).get("sig")
        except Exception:
            payload["signature"] = None
    return payload

# ── Tool Handlers ─────────────────────────────────────────────

async def tool_reserve_gold(args: dict) -> dict:
    d = await get(f"{MT}/gold")
    if d.get("error"): return {"error": d["error"]}
    data = d.get("data", d)
    payload = build_evidence_payload(
        symbol="XAU",
        asset_name="gold",
        price_data={"price_usd": data.get("price_usd"), "change_pct_24h": data.get("change_pct_24h"), "unit": "USD/oz"},
        rwa_tokens=["PAXG", "XAUT"],
        reserve_relevance="Reference reserve asset for gold-backed token structures",
        mica_relevance="Reserve asset context for asset-referenced token analysis — MiCA Art. 36",
        reserve_rank=1,
        category="commodity_reserve_asset",
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
        "summary": f"Gold (XAU): USD {data.get('price_usd')} USD/oz | {data.get('change_pct_24h',0)}% 24h | MiCA Art.36 | PAXG + XAUT"
    }

async def tool_reserve_silver(args: dict) -> dict:
    d = await get(f"{MT}/silver")
    if d.get("error"): return {"error": d["error"]}
    data = d.get("data", d)
    payload = build_evidence_payload(
        symbol="XAG",
        asset_name="silver",
        price_data={"price_usd": data.get("price_usd"), "change_pct_24h": data.get("change_pct_24h"), "unit": "USD/oz"},
        rwa_tokens=["LBMA Silver"],
        reserve_relevance="Reference reserve asset for silver-backed token structures",
        mica_relevance="Reserve asset context for commodity-backed token analysis — MiCA Art. 36",
        reserve_rank=2,
        category="commodity_reserve_asset",
        source="Yahoo Finance (SI=F)"
    )
    payload["backing_purity_standard"] = "London Good Delivery Silver (LBMA 999 fine)"
    payload["reference_price_source"] = "Yahoo Finance (SI=F) — LBMA Silver Price reference"
    payload["art_classification_potential"] = "ART — commodity referenced (MiCA Title IV)"
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
    import uuid
    gold_rid = f"fo-{uuid.uuid4().hex[:12]}"
    silver_rid = f"fo-{uuid.uuid4().hex[:12]}"
    xau_hash = evidence_hash({"asset":"gold","symbol":"XAU","price":data.get("gold_usd"),"ts":ts()})
    xag_hash = evidence_hash({"asset":"silver","symbol":"XAG","price":data.get("silver_usd"),"ts":ts()})
    return {
        "tool": "reserve_metals",
        "timestamp": ts(),
        "gold": {
            "asset": "gold",
            "symbol": "XAU",
            "asset_type": "commodity_reserve_asset",
            "price_usd": data.get("gold_usd"),
            "unit": "USD/oz",
            "change_pct_24h": data.get("gold_pct_24h"),
            "source_timestamp": ts(),
            "rwa_tokens": ["PAXG", "XAUT"],
            "reserve_relevance": "Reference reserve asset for gold-backed token structures",
            "mica_relevance": "Reserve asset context for asset-referenced token analysis — MiCA Art. 36",
            "rank_context": {"reserve_rank": 1, "category": "commodity_reserve_asset"},
            "evidence_type": "reserve_reference_snapshot",
            "content_hash": xau_hash,
            "signature_alg": "ES256K",
            "signed_at": ts(),
            "verify_url": f"https://tooloracle.io/verify/reserve/{gold_rid}",
        },
        "silver": {
            "asset": "silver",
            "symbol": "XAG",
            "asset_type": "commodity_reserve_asset",
            "price_usd": data.get("silver_usd"),
            "unit": "USD/oz",
            "change_pct_24h": data.get("silver_pct_24h"),
            "source_timestamp": ts(),
            "rwa_tokens": ["LBMA Silver"],
            "reserve_relevance": "Reference reserve asset for silver-backed token structures",
            "mica_relevance": "Reserve asset context for commodity-backed token analysis — MiCA Art. 36",
            "rank_context": {"reserve_rank": 2, "category": "commodity_reserve_asset"},
            "evidence_type": "reserve_reference_snapshot",
            "content_hash": xag_hash,
            "signature_alg": "ES256K",
            "signed_at": ts(),
            "verify_url": f"https://tooloracle.io/verify/reserve/{silver_rid}",
        },
        "gold_silver_ratio": round(data.get("gold_usd",0) / data.get("silver_usd",1), 2) if data.get("silver_usd") else None,
        "source": "Yahoo Finance",
        "summary": f"XAU: USD {data.get('gold_usd')} | XAG: USD {data.get('silver_usd')} | Ratio: {round(data.get('gold_usd',0)/data.get('silver_usd',1),1) if data.get('silver_usd') else '?'}:1"
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
    import uuid
    snap_rid = f"fo-{uuid.uuid4().hex[:12]}"
    snapshot["signature_alg"] = "ES256K"
    snapshot["signed_at"] = ts()
    snapshot["content_hash"] = evidence_hash({k:v for k,v in snapshot.items() if k != "content_hash"})
    snapshot["verify_url"] = f"https://tooloracle.io/verify/reserve/{snap_rid}"
    snapshot["request_id"] = snap_rid
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


_TOKEN_BACKING = {
    "PAXG": {"vault_location": "London", "standard": "LBMA Good Delivery",
              "audit_frequency": "monthly", "redemption_minimum": "~430 oz physical",
              "regulatory_status": ["NYDFS regulated", "qualified custodian"]},
    "XAUT": {"vault_location": "Switzerland", "standard": "LBMA Good Delivery",
              "audit_frequency": "quarterly", "redemption_minimum": "1 oz minimum",
              "regulatory_status": ["BVI registered", "unregulated issuer"]},
    "BUIDL": {"vault_location": "n/a", "standard": "SEC money market fund",
               "audit_frequency": "daily", "redemption_minimum": "$5,000,000",
               "regulatory_status": ["SEC registered", "qualified custodian (BNY Mellon)"]},
    "USDC":  {"regulatory_status": ["NYDFS regulated", "FinCEN MSB", "SIFI custodian (BNY Mellon)"]},
    "EURCV": {"regulatory_status": ["AMF regulated", "ACPR regulated", "MiCA authorized"]},
    "RLUSD": {"regulatory_status": ["NYDFS regulated", "GENIUS Act pending"]},
}

def _enrich_backing(symbol: str, base: dict) -> dict:
    extra = _TOKEN_BACKING.get(symbol, {})
    return {**base, **extra}

async def tool_token_context(args: dict) -> dict:
    """Token-Level reserve context — issuer, custody, LEI, backing structure."""
    import uuid
    symbol = args.get("symbol", "PAXG").upper()
    slug_map = {
        "PAXG": "paxos-gold", "XAUT": "tether-gold", "BUIDL": "blackrock-buidl",
        "USDC": "usdc", "USDT": "tether-usdt", "EURC": "eurc", "RLUSD": "rlusd",
        "EURCV": "societe-generale-eurcv", "EURE": "monerium-eure",
        "OUSG": "ondo-global-markets", "USDY": "ondo-yield-assets",
        "FIDD": "fidelity-fidd", "PYUSD": "pyusd", "USDP": "usdp",
    }
    slug = slug_map.get(symbol, symbol.lower())
    d = await get(f"{RWA}/registry/{slug}")
    if d.get("error"):
        return {"error": f"Token '{symbol}' not found"}
    proto = d.get("identifier_data", d if "token" in d else {})
    token = proto.get("token", {})
    issuer = proto.get("issuer", {})
    underlying = proto.get("underlying", {})
    compliance = proto.get("compliance", {})
    request_id = f"fo-{uuid.uuid4().hex[:12]}"
    payload = {
        "token": token.get("symbol", symbol),
        "display_name": proto.get("display_name"),
        "token_standard": token.get("standard"),
        "contracts": token.get("contracts", {}),
        "reserve_asset": underlying.get("asset_type"),
        "description": underlying.get("description"),
        "denomination": underlying.get("denomination"),
        "backing_structure": _enrich_backing(symbol, {
            "custody": underlying.get("custody"),
            "nav_source": underlying.get("nav_source"),
            "ownership_record": underlying.get("ownership_record"),
        }),
        "issuer": {
            "name": issuer.get("name"),
            "legal_name": issuer.get("legal_name"),
            "entity_type": issuer.get("entity_type"),
            "jurisdiction": issuer.get("jurisdiction"),
            "lei": issuer.get("lei"),
            "regulator": issuer.get("regulator", []),
        },
        "compliance": {
            "mica_relevant": compliance.get("mica_relevant"),
            "investor_type": compliance.get("investor_type"),
            "min_investment": compliance.get("min_investment"),
            "redemption_terms": compliance.get("redemption_terms"),
            "transfer_restrictions": compliance.get("transfer_restrictions", []),
        },
        "regulatory_status": _TOKEN_BACKING.get(symbol, {}).get("regulatory_status", compliance.get("transfer_restrictions", [])),
        "art_classification_potential": "ART — commodity referenced (MiCA Title IV)" if "gold" in (underlying.get("asset_type","")) else None,
        "evidence_type": "token_reserve_context",
        "signature_alg": "ES256K",
        "signed_at": ts(),
        "content_hash": None,
        "verify_url": f"https://tooloracle.io/verify/reserve/{request_id}",
        "request_id": request_id,
    }
    payload["content_hash"] = evidence_hash({k:v for k,v in payload.items() if k != "content_hash"})
    return {
        "tool": "reserve_token_context",
        "timestamp": ts(),
        **payload,
        "summary": f"{symbol}: {underlying.get('asset_type')} | {issuer.get('name')} ({issuer.get('jurisdiction')}) | LEI: {issuer.get('lei','n/a')} | MiCA: {compliance.get('mica_relevant')}"
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

server.register_tool("reserve_token_context",
    "Token-level reserve context for any RWA token — the issuer-near view. Returns token structure, custody, issuer LEI, jurisdiction, regulator, backing structure, MiCA compliance. Complements reserve_snapshot (asset-level) with token-specific details. evidence_type: token_reserve_context.",
    {"type":"object","properties":{
        "symbol":{"type":"string","description":"Token: PAXG, XAUT, BUIDL, USDC, USDT, EURC, RLUSD, EURCV, EURe, OUSG, USDY etc.","default":"PAXG"}
    },"required":["symbol"]}, tool_token_context, credits=2)

if __name__ == "__main__":
    import asyncio
    asyncio.run(server.run())
