# architecture-map-builder

Walk a monorepo / repo collection, detect services, infer dependencies, emit Mermaid + service catalog.

## Run

```bash
python map.py --path /path/to/repos --out ./out
cat out/architecture.mmd | head
cat out/report.md
```

See [SKILL.md](./SKILL.md).
