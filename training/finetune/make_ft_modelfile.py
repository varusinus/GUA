#!/usr/bin/env python3
"""Write Modelfile.ft pointing Ollama at the merged fine-tuned model."""
from pathlib import Path
from make_dataset import SYSTEM  # same dir

HERE = Path(__file__).resolve().parent
content = (f"FROM ./gua-merged\n\n"
           f'SYSTEM """{SYSTEM}"""\n\n'
           f"PARAMETER temperature 0.6\nPARAMETER top_p 0.9\n")
(HERE / "Modelfile.ft").write_text(content, encoding="utf-8")
print("Wrote", HERE / "Modelfile.ft")
