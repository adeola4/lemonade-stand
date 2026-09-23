"""Extract text from .docx using zipfile (raw extraction)."""
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

docx_path = Path("/tmp/yf100m.docx")
out_path = Path("/tmp/yf100m_full_text.txt")

try:
    with zipfile.ZipFile(str(docx_path)) as z:
        # List files
        names = z.namelist()
        print(f"Files in docx: {len(names)}")
        for n in names[:10]:
            print(f"  - {n}")
        
        # Read document.xml
        with z.open("word/document.xml") as f:
            content = f.read()
            print(f"document.xml size: {len(content)} bytes")
            
            # Parse XML
            root = ET.fromstring(content)
            
            # Namespace
            ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
            
            # Extract paragraphs
            paragraphs = []
            for p in root.iter(ns + "p"):
                para_text = ""
                for t in p.iter(ns + "t"):
                    if t.text:
                        para_text += t.text
                if para_text.strip():
                    paragraphs.append(para_text.strip())
            
            full_text = "\n\n".join(paragraphs)
            out_path.write_text(full_text, encoding="utf-8")
            print(f"\nExtracted {len(paragraphs)} paragraphs, {len(full_text)} chars")
            print(f"Saved to {out_path}")
            print(f"First 300 chars: {full_text[:300]}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
