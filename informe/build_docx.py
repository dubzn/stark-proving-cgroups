"""informe/informe.md -> informe/informe.docx (Arial 11, figures embedded).

The .docx is the bridge to Google Docs: upload it to Drive, open it as a Google
Doc and copy its content into the template copy (images survive Docs-to-Docs
paste). Runs in a python:3.12-slim container via `make informe`.
"""

import re
import subprocess
from pathlib import Path

import pypandoc
from docx import Document
from docx.shared import Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "informe" / "informe.md"
OUT = ROOT / "informe" / "informe.docx"
TMP = Path("/tmp/informe_build.md")

FONT = "Arial"


def preprocess(text):
    # Drop the authoring comment at the top.
    text = re.sub(r"<!--.*?-->\s*", "", text, count=1, flags=re.S)
    # "[INSERTAR FIGURA: path]" -> an embedded image.
    return re.sub(r"\[INSERTAR FIGURA: ([^\]]+)\]", lambda m: f"![]({m.group(1)}){{width=15cm}}", text)


def style(doc):
    for name in ["Normal", "Body Text", "First Paragraph", "Compact", "Table", "Source Code"]:
        if name in [s.name for s in doc.styles]:
            st = doc.styles[name]
            st.font.name = FONT if name != "Source Code" else "Courier New"
            st.font.size = Pt(11) if name != "Source Code" else Pt(9)
    for level, size in [(1, 16), (2, 13), (3, 11)]:
        name = f"Heading {level}"
        if name in [s.name for s in doc.styles]:
            st = doc.styles[name]
            st.font.name = FONT
            st.font.size = Pt(size)
            st.font.bold = True
            st.font.color.rgb = RGBColor(0x1F, 0x3A, 0x68)


def main():
    TMP.write_text(preprocess(SRC.read_text()))
    pypandoc.convert_file(str(TMP), "docx", outputfile=str(OUT),
                          extra_args=[f"--resource-path={ROOT}"])
    doc = Document(str(OUT))
    style(doc)
    doc.save(str(OUT))
    print(OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
