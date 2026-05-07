"""CRM Opportunity Summarizer.

Reads opportunities from Salesforce/HubSpot/CSV and emits a Markdown brief per opp.

Sources:
  --source csv     Reads sample/opportunities.csv
  --source sfdc    Salesforce REST (env: SFDC_INSTANCE, SFDC_TOKEN)
  --source hubspot HubSpot CRM v3   (env: HUBSPOT_TOKEN)
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable


@dataclass
class Opp:
    id: str
    name: str
    account: str
    stage: str
    amount: float
    close_date: str
    owner: str
    last_activity_date: str
    primary_contact: str
    next_step: str
    economic_buyer: str = ""
    metrics: str = ""
    decision_criteria: str = ""
    notes: str = ""

    def days_since_activity(self) -> int | None:
        if not self.last_activity_date:
            return None
        try:
            d = datetime.fromisoformat(self.last_activity_date.replace("Z", "+00:00"))
        except Exception:
            return None
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - d).days

    def days_to_close(self) -> int | None:
        if not self.close_date:
            return None
        try:
            d = datetime.fromisoformat(self.close_date)
        except Exception:
            return None
        return (d.date() - datetime.now(timezone.utc).date()).days


def load_csv(path: str) -> list[Opp]:
    out: list[Opp] = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            out.append(
                Opp(
                    id=r.get("id", ""),
                    name=r.get("name", ""),
                    account=r.get("account", ""),
                    stage=r.get("stage", ""),
                    amount=float(r.get("amount") or 0),
                    close_date=r.get("close_date", ""),
                    owner=r.get("owner", ""),
                    last_activity_date=r.get("last_activity_date", ""),
                    primary_contact=r.get("primary_contact", ""),
                    next_step=r.get("next_step", ""),
                    economic_buyer=r.get("economic_buyer", ""),
                    metrics=r.get("metrics", ""),
                    decision_criteria=r.get("decision_criteria", ""),
                    notes=r.get("notes", ""),
                )
            )
    return out


def fetch_salesforce(query: str | None = None) -> list[Opp]:
    import requests  # type: ignore

    inst = os.environ["SFDC_INSTANCE"].rstrip("/")
    tok = os.environ["SFDC_TOKEN"]
    soql = query or (
        "SELECT Id,Name,Account.Name,StageName,Amount,CloseDate,Owner.Name,"
        "LastActivityDate,NextStep FROM Opportunity WHERE IsClosed=false LIMIT 50"
    )
    r = requests.get(
        f"{inst}/services/data/v59.0/query",
        params={"q": soql},
        headers={"Authorization": f"Bearer {tok}"},
        timeout=30,
    )
    r.raise_for_status()
    out: list[Opp] = []
    for rec in r.json().get("records", []):
        out.append(
            Opp(
                id=rec.get("Id", ""),
                name=rec.get("Name", ""),
                account=(rec.get("Account") or {}).get("Name", ""),
                stage=rec.get("StageName", ""),
                amount=float(rec.get("Amount") or 0),
                close_date=rec.get("CloseDate", ""),
                owner=(rec.get("Owner") or {}).get("Name", ""),
                last_activity_date=rec.get("LastActivityDate", "") or "",
                primary_contact="",
                next_step=rec.get("NextStep", "") or "",
            )
        )
    return out


def fetch_hubspot() -> list[Opp]:
    import requests  # type: ignore

    tok = os.environ["HUBSPOT_TOKEN"]
    r = requests.get(
        "https://api.hubapi.com/crm/v3/objects/deals",
        headers={"Authorization": f"Bearer {tok}"},
        params={"limit": 50, "properties": "dealname,amount,dealstage,closedate,hubspot_owner_id,notes_last_updated"},
        timeout=30,
    )
    r.raise_for_status()
    out: list[Opp] = []
    for d in r.json().get("results", []):
        p = d.get("properties", {})
        out.append(
            Opp(
                id=d.get("id", ""),
                name=p.get("dealname", ""),
                account="",
                stage=p.get("dealstage", ""),
                amount=float(p.get("amount") or 0),
                close_date=p.get("closedate", "")[:10] if p.get("closedate") else "",
                owner=p.get("hubspot_owner_id", ""),
                last_activity_date=p.get("notes_last_updated", "")[:10] if p.get("notes_last_updated") else "",
                primary_contact="",
                next_step="",
            )
        )
    return out


def risks(o: Opp) -> list[str]:
    out: list[str] = []
    days = o.days_since_activity()
    if days is not None and days > 14:
        out.append(f"**Stalled** — no activity in {days} days")
    if not o.economic_buyer:
        out.append("Economic buyer not identified (MEDDIC gap)")
    if not o.metrics:
        out.append("Quantified business impact / metrics missing")
    if not o.decision_criteria:
        out.append("Decision criteria not documented")
    dtc = o.days_to_close()
    if dtc is not None and dtc < 14 and o.stage.lower() not in {"closed won", "negotiation", "contract"}:
        out.append(f"Close date in {dtc} days but stage is **{o.stage}** — likely slip")
    return out


def next_best_action(o: Opp) -> str:
    if o.days_since_activity() is not None and (o.days_since_activity() or 0) > 14:
        return f"Multi-thread: send a value re-engagement email to {o.primary_contact or 'primary contact'} and request a 30-min next step within 5 business days."
    if not o.economic_buyer:
        return "Identify the economic buyer; ask champion for an intro on the next call."
    if not o.metrics:
        return "Quantify ROI: align with champion on baseline metrics and target uplift."
    return f"Confirm next step: {o.next_step or 'set a concrete next meeting with a date and agenda'}."


def render(o: Opp) -> str:
    lines = [
        f"## {o.account or '(no account)'} — {o.name}",
        f"**Stage:** {o.stage} | **Amount:** ${o.amount:,.0f} | **Close:** {o.close_date or 'TBD'} | **Owner:** {o.owner or 'TBD'}",
        "",
        f"**TL;DR:** {o.stage} stage deal worth ${o.amount:,.0f} with close date {o.close_date or 'TBD'}.",
        "",
        f"**Primary contact:** {o.primary_contact or 'not set'}",
        f"**Last activity:** {o.last_activity_date or 'unknown'}",
        "",
        "**Risks:**",
    ]
    rs = risks(o)
    if rs:
        lines += [f"- {r}" for r in rs]
    else:
        lines.append("- None flagged")
    lines += ["", f"**Next best action:** {next_best_action(o)}", ""]
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", choices=["csv", "sfdc", "hubspot"], required=True)
    p.add_argument("--csv", default="sample/opportunities.csv")
    p.add_argument("--soql", default=None)
    p.add_argument("--out", default="-")
    args = p.parse_args()

    if args.source == "csv":
        opps = load_csv(args.csv)
    elif args.source == "sfdc":
        opps = fetch_salesforce(args.soql)
    else:
        opps = fetch_hubspot()

    body = "# Opportunity Briefs\n\n" + "\n---\n".join(render(o) for o in opps)
    if args.out == "-":
        print(body)
    else:
        with open(args.out, "w") as f:
            f.write(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
