import json
from pathlib import Path

nb_path = Path(__file__).parent.parent / "notebooks" / "ARTIFEX_v7.2_Spanish_Benchmark.ipynb"
with open(nb_path) as f:
    nb = json.load(f)

for i, cell in enumerate(nb["cells"]):
    src = "".join(cell.get("source", []))
    if "class ArtifexSwarmV72:" in src:
        print(f"--- Cell {i} (ArtifexSwarmV72) ---")
        print(src)
    if "cosine_similarity(" in src:
        print(f"--- Cell {i} (Perspectivist Alignment) ---")
        print(src)
    if "inter-rater" in src.lower() or "skew" in src.lower() or "acc(group)" in src:
        print(f"--- Cell {i} (Quality Control / Metric) ---")
        print(src)
