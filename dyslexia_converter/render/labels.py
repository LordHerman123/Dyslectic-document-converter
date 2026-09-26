"""Words the converter adds to a document (Contents, Notes, [Note 1], the 'About this version' note).

They follow the document's language, so a Dutch article gets 'Inhoud' and '[Noot 1]'. The author's own
text is never translated. Unknown languages use English.
"""
from __future__ import annotations

LABELS: dict[str, dict[str, str]] = {
    "en": {
        "table_picture": "Table (picture of the original)",
        "figure": "Figure",  # read out for a picture without a description
        "formula": "Formula",
        "contents": "Contents",
        "notes": "Notes",
        "note": "Note {n}",
        "unmatched": "Citations not matched to the reference list",
        "unreadable": "This scanned page is shown as a picture because its text could not be read reliably. "
                      "Installing Tesseract OCR usually fixes this.",
        "no_text": "(No text could be extracted from this document.)",
        "about_source": "Reformatted from “{file}” for easier reading (A4, {font} {size} pt, line spacing "
                        "{spacing}).",
        "about_wording": "The author’s wording has not been changed.",
        "about_ocr": "Some pages were scanned and converted with OCR; {n} OCR correction(s) were applied.",
        "about_citations": "Author-year citations were replaced by bracketed numbers that point to the numbered "
                           "reference list; automated citation detection can make mistakes.",
        "about_notes": "Footnotes were moved to the Notes section at the end.",
    },
    "nl": {
        "table_picture": "Tabel (afbeelding van het origineel)",
        "figure": "Figuur",  # read out for a picture without a description
        "formula": "Formule",
        "contents": "Inhoud",
        "notes": "Noten",
        "note": "Noot {n}",
        "unmatched": "Verwijzingen die niet in de literatuurlijst gevonden zijn",
        "unreadable": "Deze gescande pagina wordt als afbeelding getoond omdat de tekst niet betrouwbaar gelezen "
                      "kon worden. Tesseract OCR installeren lost dit meestal op.",
        "no_text": "(Uit dit document kon geen tekst gehaald worden.)",
        "about_source": "Opnieuw opgemaakt vanuit “{file}” om makkelijker te lezen (A4, {font} {size} pt, "
                        "regelafstand {spacing}).",
        "about_wording": "De woorden van de auteur zijn niet veranderd.",
        "about_ocr": "Sommige pagina's waren gescand en zijn met OCR omgezet; er zijn {n} OCR-correctie(s) "
                     "toegepast.",
        "about_citations": "Verwijzingen met auteur en jaar zijn vervangen door nummers tussen haken die naar de "
                           "genummerde literatuurlijst wijzen; automatische herkenning kan fouten maken.",
        "about_notes": "Voetnoten zijn verplaatst naar het deel Noten aan het einde.",
    },
    "fr": {
        "table_picture": "Tableau (image de l'original)",
        "figure": "Figure",  # read out for a picture without a description
        "formula": "Formule",
        "contents": "Sommaire",
        "notes": "Notes",
        "note": "Note {n}",
        "unmatched": "Citations absentes de la bibliographie",
        "unreadable": "Cette page numérisée est affichée en image car son texte n'a pas pu être lu de façon "
                      "fiable. Installer Tesseract OCR résout généralement ce problème.",
        "no_text": "(Aucun texte n'a pu être extrait de ce document.)",
        "about_source": "Mis en forme à partir de « {file} » pour faciliter la lecture (A4, {font} {size} pt, "
                        "interligne {spacing}).",
        "about_wording": "Le texte de l'auteur n'a pas été modifié.",
        "about_ocr": "Certaines pages étaient numérisées et ont été converties par OCR ; {n} correction(s) OCR "
                     "ont été appliquées.",
        "about_citations": "Les citations auteur-année ont été remplacées par des numéros entre crochets qui "
                           "renvoient à la bibliographie numérotée ; la détection automatique peut se tromper.",
        "about_notes": "Les notes de bas de page ont été déplacées dans la section Notes à la fin.",
    },
    "de": {
        "table_picture": "Tabelle (Bild des Originals)",
        "figure": "Abbildung",  # read out for a picture without a description
        "formula": "Formel",
        "contents": "Inhalt",
        "notes": "Anmerkungen",
        "note": "Anm. {n}",
        "unmatched": "Zitate ohne Eintrag im Literaturverzeichnis",
        "unreadable": "Diese gescannte Seite wird als Bild gezeigt, weil ihr Text nicht zuverlässig gelesen "
                      "werden konnte. Die Installation von Tesseract OCR behebt das meist.",
        "no_text": "(Aus diesem Dokument konnte kein Text gelesen werden.)",
        "about_source": "Aus „{file}“ zum leichteren Lesen neu gesetzt (A4, {font} {size} pt, Zeilenabstand "
                        "{spacing}).",
        "about_wording": "Der Wortlaut des Autors wurde nicht verändert.",
        "about_ocr": "Einige Seiten waren gescannt und wurden per OCR umgewandelt; {n} OCR-Korrektur(en) wurden "
                     "angewendet.",
        "about_citations": "Autor-Jahr-Zitate wurden durch Nummern in Klammern ersetzt, die auf das nummerierte "
                           "Literaturverzeichnis verweisen; die automatische Erkennung kann Fehler machen.",
        "about_notes": "Fußnoten wurden in den Abschnitt Anmerkungen am Ende verschoben.",
    },
    "es": {
        "table_picture": "Tabla (imagen del original)",
        "figure": "Figura",  # read out for a picture without a description
        "formula": "Fórmula",
        "contents": "Índice",
        "notes": "Notas",
        "note": "Nota {n}",
        "unmatched": "Citas que no figuran en la bibliografía",
        "unreadable": "Esta página escaneada se muestra como imagen porque su texto no se pudo leer de forma "
                      "fiable. Instalar Tesseract OCR suele solucionarlo.",
        "no_text": "(No se pudo extraer texto de este documento.)",
        "about_source": "Reformateado a partir de «{file}» para facilitar la lectura (A4, {font} {size} pt, "
                        "interlineado {spacing}).",
        "about_wording": "El texto del autor no se ha modificado.",
        "about_ocr": "Algunas páginas estaban escaneadas y se convirtieron con OCR; se aplicaron {n} "
                     "corrección(es) OCR.",
        "about_citations": "Las citas autor-año se sustituyeron por números entre corchetes que remiten a la "
                           "bibliografía numerada; la detección automática puede equivocarse.",
        "about_notes": "Las notas al pie se trasladaron a la sección Notas al final.",
    },
    "it": {
        "table_picture": "Tabella (immagine dell'originale)",
        "figure": "Figura",  # read out for a picture without a description
        "formula": "Formula",
        "contents": "Indice",
        "notes": "Note",
        "note": "Nota {n}",
        "unmatched": "Citazioni non presenti nella bibliografia",
        "unreadable": "Questa pagina scansionata è mostrata come immagine perché il testo non è stato letto in "
                      "modo affidabile. Installare Tesseract OCR di solito risolve il problema.",
        "no_text": "(Non è stato possibile estrarre testo da questo documento.)",
        "about_source": "Reimpaginato da «{file}» per una lettura più facile (A4, {font} {size} pt, interlinea "
                        "{spacing}).",
        "about_wording": "Le parole dell'autore non sono state cambiate.",
        "about_ocr": "Alcune pagine erano scansionate e sono state convertite con l'OCR; sono state applicate {n} "
                     "correzioni OCR.",
        "about_citations": "Le citazioni autore-anno sono state sostituite da numeri tra parentesi quadre che "
                           "rimandano alla bibliografia numerata; il rilevamento automatico può sbagliare.",
        "about_notes": "Le note a piè di pagina sono state spostate nella sezione Note alla fine.",
    },
    "pt": {
        "table_picture": "Tabela (imagem do original)",
        "figure": "Figura",  # read out for a picture without a description
        "formula": "Fórmula",
        "contents": "Índice",
        "notes": "Notas",
        "note": "Nota {n}",
        "unmatched": "Citações que não constam da bibliografia",
        "unreadable": "Esta página digitalizada é mostrada como imagem porque o texto não pôde ser lido de forma "
                      "fiável. Instalar o Tesseract OCR costuma resolver.",
        "no_text": "(Não foi possível extrair texto deste documento.)",
        "about_source": "Reformatado a partir de «{file}» para facilitar a leitura (A4, {font} {size} pt, "
                        "entrelinha {spacing}).",
        "about_wording": "O texto do autor não foi alterado.",
        "about_ocr": "Algumas páginas estavam digitalizadas e foram convertidas com OCR; foram aplicadas {n} "
                     "correção(ões) OCR.",
        "about_citations": "As citações autor-ano foram substituídas por números entre parênteses retos que "
                           "remetem para a bibliografia numerada; a deteção automática pode errar.",
        "about_notes": "As notas de rodapé foram movidas para a secção Notas no fim.",
    },
}


def label(lang: str, key: str, **values) -> str:
    text = LABELS.get(lang, LABELS["en"]).get(key) or LABELS["en"][key]
    return text.format(**values) if values else text
