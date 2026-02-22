# swabb — Cloud Housekeeping CLI (M1: Core AWS scanning)

**swabb** is a safe‑by‑default CLI that scans → reports → (later) cleans unused cloud resources.

This Milestone delivers:

- ✅ **AWS scanning** for:
  - **EBS volumes**: detect *unattached* (`status=available`) volumes older than N days
  - **Elastic IPs**: detect *unassociated* addresses
- ✅ **Plan output** (JSON) + **pretty table** on the console
- ✅ **Pricing stub/cache** with **config fallback** (no Pricing API calls yet)
- ✅ **Unit & E2E tests** powered by **botocore Stubber**

## Quick start (from source)

```bash
# Bootstrap a venv and run the CLI from source
./scripts/run-swabb.sh scan -t ebs,eip --regions us-east-1 --older-than 30 --cost --output table

# JSON plan + write to disk
./scripts/run-swabb.sh scan -t ebs,eip --regions us-east-1 --older-than 30 --cost --output json --plan-out plan.json
