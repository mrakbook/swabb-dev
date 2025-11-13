from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import boto3
from botocore.config import Config as BotoConfig


@dataclass
class AwsContext:
    profile: Optional[str]
    account_label: str
    region: str
    ec2: object  # botocore client


def get_ec2_client(region: str, profile: Optional[str]) -> object:
    if profile:
        sess = boto3.Session(profile_name=profile)
    else:
        sess = boto3.Session()
    cfg = BotoConfig(retries={"mode": "standard", "max_attempts": 10})
    return sess.client("ec2", region_name=region, config=cfg)


def build_ctx(region: str, profile: Optional[str], account_label: str) -> AwsContext:
    ec2 = get_ec2_client(region, profile)
    return AwsContext(profile=profile, account_label=account_label, region=region, ec2=ec2)
