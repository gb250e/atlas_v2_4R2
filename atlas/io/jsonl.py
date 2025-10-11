from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, Iterator

def read_jsonl(path: str) -> Iterator[Dict[str, Any]]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"JSONL not found: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line=line.strip()
            if not line: 
                continue
            yield json.loads(line)

def write_jsonl(path: str, rows: Iterable[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
