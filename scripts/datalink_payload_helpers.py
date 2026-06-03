from __future__ import annotations

import base64
import json
import zlib
from typing import Dict, List, Tuple


def udp_relay_image_bytes_from_entry(raw: object) -> Tuple[bytes, str, str]:
    if not isinstance(raw, dict):
        return (b"", "image/png", "")
    mime = str(raw.get("mime", "image/png")).strip() or "image/png"
    name = str(raw.get("name", "")).strip()
    data_b64 = str(raw.get("data_b64", raw.get("data", raw.get("b64", "")))).strip()
    if data_b64 == "":
        return (b"", mime, name)
    if "," in data_b64 and data_b64.lower().startswith("data:"):
        data_b64 = data_b64.split(",", 1)[1].strip()
    try:
        blob = base64.b64decode(data_b64, validate=False)
        if isinstance(blob, (bytes, bytearray)):
            return (bytes(blob), mime, name)
    except Exception:
        return (b"", mime, name)
    return (b"", mime, name)


def udp_relay_referenced_image_tokens(net_payload: object) -> List[str]:
    out: List[str] = []
    if not isinstance(net_payload, dict):
        return out
    missions = net_payload.get("missions", {})
    if not isinstance(missions, dict):
        return out
    store = missions.get("store", {})
    if not isinstance(store, dict):
        return out
    seen: set[str] = set()
    for _mid, raw in store.items():
        if not isinstance(raw, dict):
            continue
        imgs = raw.get("images", [])
        if isinstance(imgs, list):
            for it in imgs:
                token = str(it).strip()
                if token != "" and token not in seen:
                    seen.add(token)
                    out.append(token)
        pages = raw.get("pages", [])
        if isinstance(pages, list):
            for p in pages:
                if not isinstance(p, dict):
                    continue
                if str(p.get("type", "")).strip().lower() != "image":
                    continue
                token = str(p.get("image_token", "")).strip()
                if token != "" and token not in seen:
                    seen.add(token)
                    out.append(token)
    return out


def udp_relay_pack_datalink_payload_blob(payload: object) -> Tuple[Dict[str, object], bool]:
    if not isinstance(payload, dict) or len(payload) <= 0:
        return ({"payload": {}}, False)
    try:
        raw_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    except Exception:
        return ({"payload": payload}, False)
    if len(raw_json) <= 1800:
        return ({"payload": payload}, False)
    try:
        comp = zlib.compress(raw_json, level=6)
        b64 = base64.b64encode(comp).decode("ascii")
        if len(b64) < max(1, int(len(raw_json) * 0.85)):
            return (
                {
                    "payload": {},
                    "payload_codec": "zlib+base64+json",
                    "payload_z": b64,
                    "payload_raw_bytes": int(len(raw_json)),
                },
                True,
            )
    except Exception:
        pass
    return ({"payload": payload}, False)


def udp_relay_unpack_datalink_payload_blob(dl_obj: object) -> Dict[str, object]:
    if not isinstance(dl_obj, dict):
        return {}
    payload_raw = dl_obj.get("payload", {})
    if isinstance(payload_raw, dict) and len(payload_raw) > 0:
        return payload_raw
    codec = str(dl_obj.get("payload_codec", "")).strip().lower()
    if codec != "zlib+base64+json":
        return {}
    payload_z = str(dl_obj.get("payload_z", "")).strip()
    if payload_z == "":
        return {}
    try:
        comp = base64.b64decode(payload_z, validate=False)
        raw = zlib.decompress(comp)
        parsed = json.loads(raw.decode("utf-8", errors="ignore"))
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return {}
