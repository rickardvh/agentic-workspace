"""Render a signed review-authority receipt for a trusted reviewer host."""

from __future__ import annotations

import argparse
import os
import secrets
from collections.abc import Sequence

from review_merge_gate import REVIEW_AUTHORITY_MARKER_RE, sign_authority_receipt


def render_receipt(
    *,
    secret: str,
    key_id: str,
    producer_class: str,
    producer: str,
    pr_number: int,
    head_sha: str,
    decision: str,
    nonce: str,
) -> str:
    signature = sign_authority_receipt(
        secret=secret,
        key_id=key_id,
        producer_class=producer_class,
        producer=producer,
        pr_number=pr_number,
        head_sha=head_sha,
        decision=decision,
        nonce=nonce,
    )
    marker = (
        f"<!-- aw-review-authority-v1 key={key_id} class={producer_class} producer={producer} "
        f"pr={pr_number} head={head_sha} decision={decision} nonce={nonce} signature={signature} -->"
    )
    if REVIEW_AUTHORITY_MARKER_RE.fullmatch(marker) is None:
        raise ValueError("receipt fields contain unsupported characters")
    return marker


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--decision", choices=("blocked", "merge-ready"), required=True)
    parser.add_argument(
        "--producer-class",
        choices=("human", "independent", "separate-actor", "fresh-context", "distinct-provider"),
        required=True,
    )
    parser.add_argument("--producer", required=True)
    parser.add_argument("--key-id", default="primary")
    parser.add_argument("--key-env", default="AW_REVIEW_AUTHORITY_KEY")
    parser.add_argument("--nonce", default="")
    args = parser.parse_args(argv)
    secret = os.environ.get(args.key_env, "")
    if not secret:
        parser.error(f"trusted reviewer host did not provide {args.key_env}")
    print(
        render_receipt(
            secret=secret,
            key_id=args.key_id,
            producer_class=args.producer_class,
            producer=args.producer,
            pr_number=args.pr,
            head_sha=args.head,
            decision=args.decision,
            nonce=args.nonce or secrets.token_hex(16),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
