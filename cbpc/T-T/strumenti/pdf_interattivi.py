"""Rende interrogabili gli schemi PDF dei nodi.

Aggiunge in coda al PDF (aggiornamento incrementale: i byte del disegno
originale restano intatti) dei pulsanti trasparenti, senza bordo ne'
riempimento, sopra i componenti del disegno. Al clic si apre un riquadro
con il dato della verifica nodi (app.alert, supportato da Acrobat/Reader e
dal visualizzatore PDF di Chrome/Edge). Al passaggio del mouse compare anche
il suggerimento (/TU) con lo stesso testo.

Uso:  python3 strumenti/pdf_interattivi.py 413 [altri nodi]   (da cbpc/T-T)
      python3 strumenti/pdf_interattivi.py 413 --prova       -> aree rosse visibili
Il PDF di partenza deve essere quello originale, senza aree gia' aggiunte.
"""
import json
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (ArrayObject, BooleanObject, DecodedStreamObject,
                           DictionaryObject, FloatObject, NameObject,
                           NumberObject, TextStringObject)

BASE = Path(__file__).resolve().parent.parent


def js_str(s):
    return json.dumps(s, ensure_ascii=True)  # stringa JS con escape \uXXXX


def appearance(writer, w, h, prova):
    s = DecodedStreamObject()
    s.set_data(b"1 0 0 RG 1 w 0.5 0.5 %.2f %.2f re S" % (w - 1, h - 1) if prova else b"")
    s.update({NameObject("/Type"): NameObject("/XObject"),
              NameObject("/Subtype"): NameObject("/Form"),
              NameObject("/BBox"): ArrayObject([FloatObject(0), FloatObject(0), FloatObject(w), FloatObject(h)])})
    return writer._add_object(s)


def rendi_interattivo(nodo, cfg, prova=False, out=None):
    src = BASE / cfg["pdf"]
    reader = PdfReader(src)
    if "/AcroForm" in reader.trailer["/Root"]:
        sys.exit(f"{src.name}: ha gia' un modulo/aree, parti dal PDF originale")
    writer = PdfWriter(clone_from=src) if prova else PdfWriter(src, incremental=True)
    page = writer.pages[0]
    annots = page.get("/Annots")
    annots = annots.get_object() if annots is not None else ArrayObject()
    fields = ArrayObject()
    for i, area in enumerate(cfg["aree"]):
        x1, y1, x2, y2 = area["rect"]
        testo = cfg["dati"][area["dato"]] or "Dato mancante"
        js = "app.alert({cMsg: %s, cTitle: %s, nIcon: 3});" % (js_str(testo), js_str(cfg["titolo"]))
        action = DictionaryObject({NameObject("/S"): NameObject("/JavaScript"),
                                   NameObject("/JS"): TextStringObject(js)})
        ap = DictionaryObject({NameObject("/N"): appearance(writer, x2 - x1, y2 - y1, prova)})
        w = DictionaryObject({
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Widget"),
            NameObject("/FT"): NameObject("/Btn"),
            NameObject("/Ff"): NumberObject(65536),  # pulsante
            NameObject("/T"): TextStringObject(f"nodo{nodo}_{area['dato']}_{i + 1}"),
            NameObject("/TU"): TextStringObject(testo.replace("\n", " - ")),
            NameObject("/Rect"): ArrayObject([FloatObject(v) for v in (x1, y1, x2, y2)]),
            NameObject("/F"): NumberObject(4),  # stampabile; il pulsante non disegna nulla
            NameObject("/H"): NameObject("/N"),
            NameObject("/MK"): DictionaryObject(),
            NameObject("/AP"): ap,
            NameObject("/A"): action,
            NameObject("/P"): page.indirect_reference,
        })
        ref = writer._add_object(w)
        annots.append(ref)
        fields.append(ref)
    page[NameObject("/Annots")] = annots
    writer._root_object[NameObject("/AcroForm")] = writer._add_object(DictionaryObject({
        NameObject("/Fields"): fields,
        NameObject("/NeedAppearances"): BooleanObject(False),
    }))
    dest = out or src
    with open(dest, "wb") as f:
        writer.write(f)
    print(f"{dest}: {len(cfg['aree'])} aree")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    prova = "--prova" in sys.argv
    cfg = json.loads((BASE / "strumenti/aree_nodi.json").read_text(encoding="utf-8"))["nodi"]
    for n in args:
        out = None
        if prova:
            out = Path.cwd() / f"prova_{n}.pdf"
        rendi_interattivo(n, cfg[n], prova, out)
