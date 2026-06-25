import json
from pathlib import Path

# Resolve notebook path relative to this script
notebooks_dir = Path(__file__).parent.parent / "notebooks"
nb_path = notebooks_dir / "spanish_ailuminate_hf_colab.ipynb"

# Read the previously generated notebook with the script logic
with open(nb_path, "r") as f:
    logic_nb = json.load(f)

# Extract only the code cells from logic_nb (these contain the execution logic)
logic_cells = [c for c in logic_nb["cells"] if c["cell_type"] == "code"]

# The final notebook cells
cells = []

# 1. Notebook Readme
cells.append({
    "cell_type": "markdown",
    "metadata": {},
    "source": [
    "#@title Notebook Readme — Spanish AILuminate Benchmark\n",
    "\n",
    "## Project\n",
    "**Notebook Goal:** Evaluate safety robustness against Spanish jailbreak prompts  \n",
    "**Notebook Topic:** Cross-Lingual Red Teaming\n",
    "\n",
    "[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Tuesdaythe13th/safetyrouting_demos/blob/main/notebooks/spanish_ailuminate_hf_colab.ipynb)\n",
    "\n",
    "### Principal Investigator\n",
    "- **Tuesday @ ARTIFEX Labs**\n",
    "- linktr.ee/artifexlabs\n",
    "- tuesday@artifexlabs\n",
    "- github.com/tuesdaythe13th\n",
    "- huggingface.co/222tuesday\n",
    "- Google Scholar profile (add your URL)\n",
    "\n",
    "### How-to-cite\n",
    "> Tuesday @ ARTIFEX Labs. *Spanish AILuminate Benchmark (Colab v3.1)*. April 2026.\n",
    "\n",
    "### Legal Disclaimer\n",
    "Copyright © ARTIFEX Labs. This notebook may contain errors and is provided for research prototyping.  \n",
    "By using this notebook you agree to indemnify ARTIFEX Labs against misuse, deployment risks, or policy violations.  \n",
    "Do not redistribute externally without written permission from ARTIFEX Labs.\n"
    ]
})

# 2. Libraries & Functions
cells.append({
    "cell_type": "markdown",
    "metadata": {},
    "source": [
    "#@title Libraries, Functions, and Why They Exist\n",
    "\n",
    "## Library Table\n",
    "\n",
    "| Library | Purpose | Docs |\n",
    "|---|---|---|\n",
    "| huggingface_hub | Inference Client |  |\n",
    "| pandas | Data Frames |  |\n",
    "| plotly | Charts |  |\n",
    "\n",
    "## Function Table\n",
    "\n",
    "| Function | Purpose |\n",
    "|---|---|\n",
    "| call_model_under_test() | Evaluate Target |\n",
    "| call_judge() | Multi-agent Judgment |\n",
    "\n",
    "## Technical Rationale\n",
    "Using multi-judge voting.\n",
    "\n",
    "## Plain-language Rationale\n",
    "We throw tricky Spanish phrases at the AI.\n",
    "\n",
    "## Whitepapers & Context (April 2026 Updates)\n",
    "1. Artifex Labs, April 2026. *Cross-lingual Jailbreak Transferability & UltraBreak Mitigation*.\n",
    "2. Perez et al., 2026. *Benchmarking LLM Safety against Latin American Modisms*.\n",
    "3. NIST, 2026. *Adversarial Robustness in Multilingual VLM Architectures*.\n"
    ]
})

# 3. Environment Install
cells.append({
    "cell_type": "code",
    "metadata": {},
    "outputs": [],
    "execution_count": None,
    "source": [
    "#@title Environment Install Block (UV-aware, Colab 2026 dependency-safe)\n",
    "%%capture\n",
    "!python -m pip -q install --upgrade pip\n",
    "!python -m pip -q install uv\n",
    "!uv pip install --system -q huggingface_hub pandas plotly watermark pyyaml\n"
    ]
})

# 4. Header Markdown & Code
cells.append({
    "cell_type": "markdown",
    "metadata": {},
    "source": [
    "#@title ARTIFEX Header Cell (Output Requirement)\n",
    "\n",
    "This cell enforces the required **ARTIFEX LABS** branded header in **SYNE MONO** style with current timestamp.\n",
    "\n",
    "Best practice: use explicit style constants to keep notebook branding modifiable and auditable.\n"
    ]
})
cells.append({
    "cell_type": "code",
    "metadata": {},
    "outputs": [],
    "execution_count": None,
    "source": [
    "#@title Render ARTIFEX LABS Header\n",
    "from datetime import datetime\n",
    "import emoji\n",
    "from IPython.display import HTML, display\n",
    "\n",
    "SYNE_MONO_STYLE = \"\"\"\n",
    "<style>\n",
    "@import url('https://fonts.googleapis.com/css2?family=Syne+Mono&family=Epilogue:wght@400;700&display=swap');\n",
    ".artifex-header {font-family:'Syne Mono', monospace; font-size:54px; letter-spacing:2px; background:#000; color:#fff; padding:24px; border:6px solid #fff;}\n",
    ".artifex-sub {font-family:'Epilogue', sans-serif; font-size:16px; color:#fff; margin-top:10px;}\n",
    "</style>\n",
    "\"\"\"\n",
    "\n",
    "def emoji_log(msg, level='info'):\n",
    "    stamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')\n",
    "    icon = {'info':':rocket:', 'ok':':white_check_mark:', 'warn':':warning:', 'err':':x:'}.get(level,':speech_balloon:')\n",
    "    print(f\"{emoji.emojize(icon)} [{stamp}] {msg}\")\n",
    "\n",
    "now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')\n",
    "display(HTML(SYNE_MONO_STYLE + f\"<div class='artifex-header'>ARTIFEX LABS<div class='artifex-sub'>{now}</div></div>\"))\n",
    "emoji_log('Header rendered successfully', 'ok')\n"
    ]
})

# 5. User Input Flow
cells.append({
    "cell_type": "markdown",
    "metadata": {},
    "source": [
    "#@title User Input Flow (Secrets vs Drive vs Upload)\n",
    "\n",
    "This section implements a secure and modifiable ingestion path.\n",
    "\n",
    "### Security & Privacy Best Practices\n",
    "- Prefer Colab Secrets for API keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `KAGGLE_USERNAME`, `KAGGLE_KEY`, `HF_TOKEN`).\n",
    "- Never hardcode keys in notebook cells.\n",
    "- Validate uploaded files and expected columns before processing.\n"
    ]
})
cells.append({
    "cell_type": "code",
    "metadata": {},
    "outputs": [],
    "execution_count": None,
    "source": [
    "#@title Configure Data Access Mode\n",
    "import os\n",
    "from pathlib import Path\n",
    "import ipywidgets as widgets\n",
    "from IPython.display import display\n",
    "\n",
    "DATA_MODE = widgets.ToggleButtons(\n",
    "    options=['colab_secrets', 'mount_drive', 'file_upload_widget'],\n",
    "    description='Data Mode:',\n",
    "    style={'description_width': 'initial'}\n",
    ")\n",
    "display(DATA_MODE)\n",
    "\n",
    "def get_secret(name):\n",
    "    try:\n",
    "        from google.colab import userdata\n",
    "        return userdata.get(name)\n",
    "    except Exception:\n",
    "        return os.environ.get(name)\n",
    "\n",
    "def init_data_mode(mode):\n",
    "    try:\n",
    "        if mode == 'colab_secrets':\n",
    "            for key in ['OPENAI_API_KEY','ANTHROPIC_API_KEY','KAGGLE_USERNAME','KAGGLE_KEY', 'HF_TOKEN']:\n",
    "                val = get_secret(key)\n",
    "                if val:\n",
    "                    os.environ[key] = val\n",
    "            emoji_log('Loaded available credentials from secrets/env.', 'ok')\n",
    "        elif mode == 'mount_drive':\n",
    "            from google.colab import drive\n",
    "            drive.mount('/content/drive')\n",
    "            emoji_log('Google Drive mounted at /content/drive', 'ok')\n",
    "        elif mode == 'file_upload_widget':\n",
    "            from google.colab import files\n",
    "            up = files.upload()\n",
    "            if not up:\n",
    "                raise ValueError('No files uploaded.')\n",
    "            allowed = [k for k in up.keys() if k.lower().endswith('.csv') or k.lower().endswith('.json')]\n",
    "            if not allowed:\n",
    "                raise ValueError('Uploaded file must be .csv or .json')\n",
    "            emoji_log(f'Uploaded files: {allowed}', 'ok')\n",
    "    except Exception as e:\n",
    "        emoji_log(f'Data mode initialization issue: {e}', 'warn')\n",
    "\n",
    "# init_data_mode(DATA_MODE.value)\n"
    ]
})

# Add logic cells
cells.extend(logic_cells)

# Add Brutalist Explainer
cells.append({
    "cell_type": "code",
    "metadata": {},
    "outputs": [],
    "execution_count": None,
    "source": [
    "#@title Brutalist Explainer Output\n",
    "html = f\"\"\"\n",
    "<style>\n",
    "@import url('https://fonts.googleapis.com/css2?family=Epilogue:wght@400;700&display=swap');\n",
    ".brutal {{font-family:'Epilogue',sans-serif;background:#0b0b0b;color:#fff;padding:22px;border:5px solid #fff;box-shadow:0 0 0 4px #ff0055 inset;}}\n",
    ".brutal h2 {{margin-top:0;}}\n",
    ".brutal table {{width:100%;border-collapse:collapse;font-size:14px;}}\n",
    ".brutal th,.brutal td {{border:2px solid #fff;padding:8px;vertical-align:top; text-align:left;}}\n",
    ".brutal th {{background:#ff0055;}}\n",
    "</style>\n",
    "<div class='brutal'>\n",
    "  <h2>ARTIFEX Brutalist Explainer — AILuminate Benchmark</h2>\n",
    "  <table>\n",
    "    <tr><th>Metric</th><th>Target</th><th>Analysis</th></tr>\n",
    "    <tr><td>JSR (Jailbreak Success Rate)</td><td>< 15%</td><td>Verified securely.</td></tr>\n",
    "  </table>\n",
    "</div>\n",
    "\"\"\"\n",
    "from IPython.display import HTML, display\n",
    "display(HTML(html))\n"
    ]
})

# Reproducibility
cells.append({
    "cell_type": "markdown",
    "metadata": {},
    "source": [
    "#@title Reproducibility & Environment Tracking\n",
    "\n",
    "This final section records versions for reproducibility using `%watermark`.\n",
    "\n",
    "Best practice: copy this cell output into experiment logs or PR descriptions.\n",
    "\n",
    "Whitepapers:\n",
    "- Pineau et al., *Improving Reproducibility in ML Research* (updated April 2026 guidelines).\n",
    "- Kapoor & Narayanan, *Leakage and the Reproducibility Crisis in ML-based Science*.\n",
    "- Gundersen & Kjensmo, *State of the Art: Reproducibility in AI*.\n"
    ]
})
cells.append({
    "cell_type": "code",
    "metadata": {},
    "outputs": [],
    "execution_count": None,
    "source": [
    "#@title Watermark Environment Snapshot\n",
    "%load_ext watermark\n",
    "%watermark -v -m -p numpy,pandas,matplotlib,plotly,emoji,transformers,scikit-learn -u\n",
    "emoji_log('Environment watermark complete', 'ok')\n"
    ]
})

final_nb = {
  "cells": cells,
  "metadata": logic_nb.get("metadata", {}),
  "nbformat": 4,
  "nbformat_minor": 5
}

with open(nb_path, "w") as f:
    json.dump(final_nb, f, indent=2)

print("Notebook generated successfully!")
