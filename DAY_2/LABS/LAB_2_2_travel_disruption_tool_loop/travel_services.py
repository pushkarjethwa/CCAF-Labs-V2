"""Mock airline / hotel / CRM services with a ledger and an event log. THE WORLD (mock airline, hotel and CRM). You read it; you do not edit it.

Reads  : flight_status, rebooking_options, hotel_availability, loyalty_tier   (safe to run concurrently)
Writes : rebook_flight -> book_hotel -> notify_traveler                        (each depends on the previous)

Behaviours the lab depends on (all deterministic):
  * every call sleeps for the latency in DATA/scenario.json (scaled by latency_scale)
  * the first EXECUTED rebook_flight commits the booking and then raises ServiceTimeout
    ("lost acknowledgement"). Retrying WITHOUT an idempotency key books a second seat.
  * downstream writes do not reject unconfirmed references (like many real systems); they book anyway and the
    ledger marks the entry unverified=True.
  * a thread-safe event log (seq, tool, phase, relative time) is what check.py analyses.
"""
from __future__ import annotations

import copy
import json
import threading
import time
from collections import Counter
from pathlib import Path

READ_TOOLS = ("flight_status", "rebooking_options", "hotel_availability", "loyalty_tier")
WRITE_TOOLS = ("rebook_flight", "book_hotel", "notify_traveler")
PREREQ = {"book_hotel": ("rebook_flight",), "notify_traveler": ("rebook_flight", "book_hotel")}


class ServiceTimeout(Exception):
    """The service may or may not have applied the request."""


def load_scenario(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


class TravelServices:
    def __init__(self, scenario: dict, *, latency_scale: float = 1.0):
        self.s = scenario
        self.scale = latency_scale
        self._lock = threading.Lock()
        self._seq = 0
        self._t0 = time.perf_counter()
        self.events: list[dict] = []
        self.rebookings: list[dict] = []
        self.hotels: list[dict] = []
        self.notifications: list[dict] = []
        self._idem: dict[tuple, dict] = {}
        self._executed: Counter = Counter()
        self._lose_ack = Counter({t: 1 for t in scenario.get("faults", {}).get("lose_ack_once", [])})

    # ---------------------------------------------------------------- instrumentation
    def _log(self, tool: str, phase: str, **kw) -> int:
        with self._lock:
            self._seq += 1
            self.events.append({"seq": self._seq, "tool": tool, "phase": phase,
                                "t": round(time.perf_counter() - self._t0, 4), **kw})
            return self._seq

    # ---------------------------------------------------------------- public entry
    def call(self, name: str, args: dict, *, idempotency_key: str | None = None) -> dict:
        if name not in READ_TOOLS + WRITE_TOOLS:
            raise ValueError(f"unknown tool {name!r}")
        self._log(name, "start", idem=bool(idempotency_key))
        try:
            if idempotency_key:
                with self._lock:
                    cached = self._idem.get((name, idempotency_key))
                if cached is not None:
                    self._log(name, "replay")
                    out = copy.deepcopy(cached)
                    out["replayed"] = True
                    self._log(name, "end", ok=True)
                    return out
            time.sleep(self.s["latency_s"][name] * self.scale)
            out = getattr(self, "_" + name)(**args)
            if idempotency_key and name in WRITE_TOOLS:
                with self._lock:
                    self._idem[(name, idempotency_key)] = copy.deepcopy(out)
            with self._lock:
                self._executed[name] += 1
                lose = self._lose_ack[name] > 0 and name in WRITE_TOOLS
                if lose:
                    self._lose_ack[name] -= 1
            if lose:
                self._log(name, "end", ok=False, error="timeout")
                raise ServiceTimeout(f"{name}: no acknowledgement within deadline")
            self._log(name, "end", ok=True)
            return out
        except ServiceTimeout:
            raise
        except Exception as e:
            self._log(name, "end", ok=False, error=type(e).__name__)
            raise

    # ---------------------------------------------------------------- reads
    def _flight_status(self, flight_no: str) -> dict:
        f = self.s["flight"]
        if flight_no != f["flight_no"]:
            raise ValueError(f"unknown flight {flight_no}")
        return {"tool": "flight_status", **f}

    def _rebooking_options(self, pnr: str) -> dict:
        return {"tool": "rebooking_options", "pnr": pnr, "options": self.s["rebooking_options"]}

    def _hotel_availability(self, airport: str, date: str) -> dict:
        return {"tool": "hotel_availability", "airport": airport, "date": date, "hotels": self.s["hotels"]}

    def _loyalty_tier(self, traveler_id: str) -> dict:
        t = self.s["travelers"].get(traveler_id)
        if not t:
            raise ValueError(f"unknown traveler {traveler_id}")
        return {"tool": "loyalty_tier", "traveler_id": traveler_id, "tier": t["tier"], "perks": self.s["tier_perks"][t["tier"]]}

    # ---------------------------------------------------------------- writes
    def _confirmed_refs(self) -> set[str]:
        with self._lock:
            return {r["ref"] for r in self.rebookings}

    def _rebook_flight(self, pnr: str, option_id: str) -> dict:
        opt = next((o for o in self.s["rebooking_options"] if o["option_id"] == option_id), None)
        if not opt or opt["seats_left"] <= 0:
            raise ValueError(f"option {option_id} unavailable")
        with self._lock:
            ref = f"RB-{len(self.rebookings) + 1:04d}"
            self.rebookings.append({"ref": ref, "pnr": pnr, "option_id": option_id})
        self._log("rebook_flight", "commit", ref=ref)
        return {"tool": "rebook_flight", "ref": ref, "pnr": pnr, "option_id": option_id,
                "flight_no": opt["flight_no"], "arrives": opt["arrives"]}

    def _book_hotel(self, hotel_id: str, rebook_ref: str, nights: int, guest: str) -> dict:
        h = next((x for x in self.s["hotels"] if x["hotel_id"] == hotel_id), None)
        if not h or h["rooms_left"] <= 0:
            raise ValueError(f"hotel {hotel_id} unavailable")
        verified = rebook_ref in self._confirmed_refs()
        with self._lock:
            ref = f"HB-{len(self.hotels) + 1:04d}"
            self.hotels.append({"ref": ref, "hotel_id": hotel_id, "rebook_ref": rebook_ref, "nights": nights,
                                "guest": guest, "unverified": not verified})
        self._log("book_hotel", "commit", ref=ref)
        return {"tool": "book_hotel", "ref": ref, "hotel_id": hotel_id, "nights": nights, "unverified": not verified}

    def _notify_traveler(self, traveler_id: str, rebook_ref: str, hotel_ref: str, channel: str = "sms") -> dict:
        t = self.s["travelers"].get(traveler_id)
        if not t:
            raise ValueError(f"unknown traveler {traveler_id}")
        verified = rebook_ref in self._confirmed_refs() and hotel_ref in {h["ref"] for h in self.hotels}
        with self._lock:
            ref = f"NT-{len(self.notifications) + 1:04d}"
            self.notifications.append({"ref": ref, "traveler_id": traveler_id, "rebook_ref": rebook_ref,
                                       "hotel_ref": hotel_ref, "channel": channel, "unverified": not verified})
        self._log("notify_traveler", "commit", ref=ref)
        return {"tool": "notify_traveler", "ref": ref, "channel": channel, "unverified": not verified}

    # ---------------------------------------------------------------- evidence
    def ledger(self) -> dict:
        return {"rebookings": self.rebookings, "hotels": self.hotels, "notifications": self.notifications}


def analyse(events: list[dict], ledger: dict) -> dict:
    """Facts derived from the raw event log + ledger. Used by lab.py AND check.py (trusted harness code)."""
    def span(tools):
        sel = [e for e in events if e["tool"] in tools and e["phase"] in ("start", "end")]
        starts = [e["t"] for e in sel if e["phase"] == "start"]
        ends = [e["t"] for e in sel if e["phase"] == "end"]
        return round(max(ends) - min(starts), 4) if starts and ends else None

    def intervals(tools):
        out = []
        for tool in tools:
            ss = [e for e in events if e["tool"] == tool and e["phase"] == "start"]
            ee = [e for e in events if e["tool"] == tool and e["phase"] == "end"]
            out += [(s["t"], e["t"]) for s, e in zip(ss, ee)]
        return sorted(out)

    ws = intervals(WRITE_TOOLS)
    overlap = any(ws[i][1] > ws[i + 1][0] for i in range(len(ws) - 1))
    first_commit = {}
    for e in events:
        if e["phase"] == "commit":
            first_commit.setdefault(e["tool"], e["seq"])
    order_violations = []
    for e in events:
        if e["phase"] == "start" and e["tool"] in PREREQ:
            for pre in PREREQ[e["tool"]]:
                if pre not in first_commit or first_commit[pre] > e["seq"]:
                    order_violations.append(f"{e['tool']} started before {pre} committed")
    reads_n = sum(1 for e in events if e["tool"] in READ_TOOLS and e["phase"] == "start")
    return {
        "read_phase_span_s": span(READ_TOOLS) if reads_n else None,
        "reads_executed": reads_n,
        "writes_overlap": overlap,
        "order_violations": sorted(set(order_violations)),
        "rebookings": len(ledger["rebookings"]),
        "hotel_bookings": len(ledger["hotels"]),
        "notifications": len(ledger["notifications"]),
        "unverified_entries": sum(1 for k in ("hotels", "notifications") for x in ledger[k] if x.get("unverified")),
        "replays": sum(1 for e in events if e["phase"] == "replay"),
    }
