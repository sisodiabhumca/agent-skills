# utm-campaign-governor

Vendor-neutral validator/normalizer for UTM parameters across marketing links.

## Run

```bash
python utm_campaign_governor.py \
  --input ../../samples/utm-campaign-governor/links.csv \
  --policy ../../samples/utm-campaign-governor/policy.json \
  --out /tmp/utm_governed_links.csv
```
