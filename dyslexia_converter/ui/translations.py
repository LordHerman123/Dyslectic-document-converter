"""Translations of the app's own texts, keyed by the English wording.

Each entry: English -> {"nl", "fr", "de", "es", "it"}. Keep {placeholders} exactly as in the English.
Missing entries fall back to English. tests/test_i18n.py checks that every text in the UI is translated.
"""

T: dict[str, dict[str, str]] = {
    # ---------------------------------------------------------------- AI privacy log and preview
    'Answer received': {
        'nl': 'Ontvangen antwoord',
        'fr': 'Réponse reçue',
        'de': 'Erhaltene Antwort',
        'es': 'Respuesta recibida',
        'it': 'Risposta ricevuta'},
    'Citations': {
        'nl': 'Verwijzingen',
        'fr': 'Citations',
        'de': 'Zitate',
        'es': 'Citas',
        'it': 'Citazioni'},
    'Clear log': {
        'nl': 'Logboek wissen',
        'fr': 'Effacer le journal',
        'de': 'Protokoll löschen',
        'es': 'Borrar registro',
        'it': 'Cancella registro'},
    'Document snippets sent': {
        'nl': 'Verstuurde stukjes tekst',
        'fr': 'Extraits du document envoyés',
        'de': 'Gesendete Dokumentausschnitte',
        'es': 'Fragmentos del documento enviados',
        'it': 'Estratti del documento inviati'},
    'Each request is listed with the exact text that left this device and the answer that came back. The log is kept only on this device; your API key is never part of it.': {
        'nl': 'Elke vraag staat hier met de exacte tekst die dit apparaat verliet en het antwoord dat terugkwam. Het logboek wordt alleen op dit apparaat bewaard; je API-sleutel staat er nooit in.',
        'fr': "Chaque requête est listée avec le texte exact qui a quitté cet appareil et la réponse reçue. Le journal est conservé uniquement sur cet appareil ; votre clé API n'y figure jamais.",
        'de': 'Jede Anfrage wird mit dem genauen Text, der dieses Gerät verlassen hat, und der erhaltenen Antwort aufgeführt. Das Protokoll bleibt nur auf diesem Gerät; Ihr API-Schlüssel ist nie darin enthalten.',
        'es': 'Cada consulta aparece con el texto exacto que salió de este dispositivo y la respuesta recibida. El registro se guarda solo en este dispositivo; tu clave API nunca forma parte de él.',
        'it': 'Ogni richiesta è elencata con il testo esatto che ha lasciato questo dispositivo e la risposta ricevuta. Il registro resta solo su questo dispositivo; la tua chiave API non ne fa mai parte.'},
    'Instructions and examples sent (the same for every request of this kind)': {
        'nl': 'Verstuurde instructies en voorbeelden (hetzelfde voor elke vraag van deze soort)',
        'fr': 'Instructions et exemples envoyés (identiques pour chaque requête de ce type)',
        'de': 'Gesendete Anweisungen und Beispiele (gleich für jede Anfrage dieser Art)',
        'es': 'Instrucciones y ejemplos enviados (iguales en cada consulta de este tipo)',
        'it': 'Istruzioni ed esempi inviati (uguali per ogni richiesta di questo tipo)'},
    'Nothing has been sent to an AI provider yet.': {
        'nl': 'Er is nog niets naar een AI-aanbieder gestuurd.',
        'fr': "Rien n'a encore été envoyé à un fournisseur d'IA.",
        'de': 'Bisher wurde nichts an einen KI-Anbieter gesendet.',
        'es': 'Aún no se ha enviado nada a un proveedor de IA.',
        'it': 'Non è ancora stato inviato nulla a un fornitore di IA.'},
    'OCR words': {
        'nl': 'OCR-woorden',
        'fr': 'Mots OCR',
        'de': 'OCR-Wörter',
        'es': 'Palabras OCR',
        'it': 'Parole OCR'},
    'Privacy log saved.': {
        'nl': 'Privacylogboek opgeslagen.',
        'fr': 'Journal de confidentialité enregistré.',
        'de': 'Datenschutzprotokoll gespeichert.',
        'es': 'Registro de privacidad guardado.',
        'it': 'Registro privacy salvato.'},
    'Privacy log: everything sent to the AI provider': {
        'nl': 'Privacylogboek: alles wat naar de AI-aanbieder is gestuurd',
        'fr': "Journal de confidentialité : tout ce qui a été envoyé au fournisseur d'IA",
        'de': 'Datenschutzprotokoll: alles, was an den KI-Anbieter gesendet wurde',
        'es': 'Registro de privacidad: todo lo enviado al proveedor de IA',
        'it': 'Registro privacy: tutto ciò che è stato inviato al fornitore di IA'},
    'Remove the privacy log from this device?': {
        'nl': 'Het privacylogboek van dit apparaat verwijderen?',
        'fr': 'Supprimer le journal de confidentialité de cet appareil ?',
        'de': 'Das Datenschutzprotokoll von diesem Gerät entfernen?',
        'es': '¿Eliminar el registro de privacidad de este dispositivo?',
        'it': 'Rimuovere il registro privacy da questo dispositivo?'},
    'Save log...': {
        'nl': 'Logboek opslaan...',
        'fr': 'Enregistrer le journal...',
        'de': 'Protokoll speichern...',
        'es': 'Guardar registro...',
        'it': 'Salva registro...'},
    'Save privacy log': {
        'nl': 'Privacylogboek opslaan',
        'fr': 'Enregistrer le journal de confidentialité',
        'de': 'Datenschutzprotokoll speichern',
        'es': 'Guardar registro de privacidad',
        'it': 'Salva registro privacy'},
    'Send': {
        'nl': 'Versturen',
        'fr': 'Envoyer',
        'de': 'Senden',
        'es': 'Enviar',
        'it': 'Invia'},
    'Send to the AI provider?': {
        'nl': 'Naar de AI-aanbieder sturen?',
        'fr': "Envoyer au fournisseur d'IA ?",
        'de': 'An den KI-Anbieter senden?',
        'es': '¿Enviar al proveedor de IA?',
        'it': 'Inviare al fornitore di IA?'},
    'This is exactly the document text that will be sent:': {
        'nl': 'Dit is precies de documenttekst die verstuurd wordt:',
        'fr': 'Voici exactement le texte du document qui sera envoyé :',
        'de': 'Genau dieser Dokumenttext wird gesendet:',
        'es': 'Este es exactamente el texto del documento que se enviará:',
        'it': 'Questo è esattamente il testo del documento che verrà inviato:'},
    'This session: {n} request(s), {cached} item(s) answered from earlier answers, {tin} tokens in, {tout} tokens out.': {
        'nl': 'Deze sessie: {n} vraag/vragen, {cached} item(s) beantwoord uit eerdere antwoorden, {tin} tokens in, {tout} tokens uit.',
        'fr': 'Cette session : {n} requête(s), {cached} élément(s) résolus par des réponses précédentes, {tin} jetons en entrée, {tout} jetons en sortie.',
        'de': 'Diese Sitzung: {n} Anfrage(n), {cached} Element(e) aus früheren Antworten beantwortet, {tin} Tokens hinein, {tout} Tokens heraus.',
        'es': 'Esta sesión: {n} consulta(s), {cached} elemento(s) resueltos con respuestas anteriores, {tin} tokens de entrada, {tout} tokens de salida.',
        'it': 'Questa sessione: {n} richiesta/e, {cached} elemento/i risolti con risposte precedenti, {tin} token in ingresso, {tout} token in uscita.'},
    'failed': {
        'nl': 'mislukt',
        'fr': 'échec',
        'de': 'fehlgeschlagen',
        'es': 'fallida',
        'it': 'non riuscita'},
    '{items} item(s), {chars} characters of document text, {tin} tokens in, {tout} tokens out': {
        'nl': '{items} item(s), {chars} tekens documenttekst, {tin} tokens in, {tout} tokens uit',
        'fr': '{items} élément(s), {chars} caractères du document, {tin} jetons en entrée, {tout} jetons en sortie',
        'de': '{items} Element(e), {chars} Zeichen Dokumenttext, {tin} Tokens hinein, {tout} Tokens heraus',
        'es': '{items} elemento(s), {chars} caracteres del documento, {tin} tokens de entrada, {tout} tokens de salida',
        'it': '{items} elemento/i, {chars} caratteri del documento, {tin} token in ingresso, {tout} token in uscita'},
    '{n} request(s) logged: {chars} characters of document text sent, {tin} tokens in ({cached} from cache), {tout} tokens out.': {
        'nl': '{n} vraag/vragen in het logboek: {chars} tekens documenttekst verstuurd, {tin} tokens in ({cached} uit de cache), {tout} tokens uit.',
        'fr': '{n} requête(s) enregistrée(s) : {chars} caractères du document envoyés, {tin} jetons en entrée ({cached} depuis le cache), {tout} jetons en sortie.',
        'de': '{n} Anfrage(n) protokolliert: {chars} Zeichen Dokumenttext gesendet, {tin} Tokens hinein ({cached} aus dem Cache), {tout} Tokens heraus.',
        'es': '{n} consulta(s) registradas: {chars} caracteres del documento enviados, {tin} tokens de entrada ({cached} desde la caché), {tout} tokens de salida.',
        'it': '{n} richiesta/e registrate: {chars} caratteri del documento inviati, {tin} token in ingresso ({cached} dalla cache), {tout} token in uscita.'},
    '{n} request(s) with {items} snippet(s): {chars} characters of document text. Each request also carries fixed instructions with made-up examples ({fixed} characters in all), which contain nothing from your document.': {
        'nl': '{n} vraag/vragen met {items} stukje(s) tekst: {chars} tekens documenttekst. Elke vraag bevat ook vaste instructies met verzonnen voorbeelden ({fixed} tekens in totaal), waarin niets uit je document staat.',
        'fr': '{n} requête(s) avec {items} extrait(s) : {chars} caractères du document. Chaque requête contient aussi des instructions fixes avec des exemples inventés ({fixed} caractères au total), qui ne contiennent rien de votre document.',
        'de': '{n} Anfrage(n) mit {items} Ausschnitt(en): {chars} Zeichen Dokumenttext. Jede Anfrage enthält außerdem feste Anweisungen mit erfundenen Beispielen ({fixed} Zeichen insgesamt), die nichts aus Ihrem Dokument enthalten.',
        'es': '{n} consulta(s) con {items} fragmento(s): {chars} caracteres del documento. Cada consulta lleva también instrucciones fijas con ejemplos inventados ({fixed} caracteres en total), que no contienen nada de tu documento.',
        'it': '{n} richiesta/e con {items} estratto/i: {chars} caratteri del documento. Ogni richiesta contiene anche istruzioni fisse con esempi inventati ({fixed} caratteri in tutto), che non contengono nulla del tuo documento.'},
    # ---------------------------------------------------------------- header, status, tabs
    "Open a PDF to start. Your original file is never changed.": {
        "nl": "Open een pdf om te beginnen. Je originele bestand wordt nooit gewijzigd.",
        "fr": "Ouvrez un PDF pour commencer. Votre fichier d'origine n'est jamais modifié.",
        "de": "Öffnen Sie ein PDF, um zu beginnen. Ihre Originaldatei wird nie verändert.",
        "es": "Abre un PDF para empezar. Tu archivo original nunca se modifica.",
        "it": "Apri un PDF per iniziare. Il file originale non viene mai modificato."},
    "Like the app? Buy me a coffee": {
        "nl": "Vind je de app handig? Trakteer me op een koffie",
        "fr": "Vous aimez l'appli ? Offrez-moi un café",
        "de": "Gefällt Ihnen die App? Spendieren Sie mir einen Kaffee",
        "es": "¿Te gusta la app? Invítame a un café",
        "it": "Ti piace l'app? Offrimi un caffè"},
    "Opens PayPal in your web browser (optional)": {
        "nl": "Opent PayPal in je webbrowser (vrijblijvend)",
        "fr": "Ouvre PayPal dans votre navigateur (facultatif)",
        "de": "Öffnet PayPal in Ihrem Webbrowser (freiwillig)",
        "es": "Abre PayPal en tu navegador (opcional)",
        "it": "Apre PayPal nel browser (facoltativo)"},
    "AI-assisted": {
        "nl": "Met AI-hulp", "fr": "Assisté par IA", "de": "KI-gestützt", "es": "Con ayuda de IA",
        "it": "Con assistenza IA"},
    "Local-only": {
        "nl": "Alleen lokaal", "fr": "Local uniquement", "de": "Nur lokal", "es": "Solo local", "it": "Solo locale"},
    "Local-only: nothing leaves this device": {
        "nl": "Alleen lokaal: niets verlaat dit apparaat",
        "fr": "Local uniquement : rien ne quitte cet appareil",
        "de": "Nur lokal: nichts verlässt dieses Gerät",
        "es": "Solo local: nada sale de este dispositivo",
        "it": "Solo locale: nulla lascia questo dispositivo"},
    "Where your document content is processed": {
        "nl": "Waar de inhoud van je document verwerkt wordt",
        "fr": "Où le contenu de votre document est traité",
        "de": "Wo der Inhalt Ihres Dokuments verarbeitet wird",
        "es": "Dónde se procesa el contenido de tu documento",
        "it": "Dove viene elaborato il contenuto del documento"},
    "Open PDF": {"nl": "Pdf openen", "fr": "Ouvrir un PDF", "de": "PDF öffnen", "es": "Abrir PDF", "it": "Apri PDF"},
    "Choose a PDF to convert": {
        "nl": "Kies een pdf om om te zetten", "fr": "Choisissez un PDF à convertir",
        "de": "Wählen Sie ein PDF zum Umwandeln", "es": "Elige un PDF para convertir",
        "it": "Scegli un PDF da convertire"},
    "Layout": {"nl": "Opmaak", "fr": "Mise en page", "de": "Layout", "es": "Diseño", "it": "Impaginazione"},
    "Preview": {"nl": "Voorbeeld", "fr": "Aperçu", "de": "Vorschau", "es": "Vista previa", "it": "Anteprima"},
    "Convert": {"nl": "Omzetten", "fr": "Convertir", "de": "Umwandeln", "es": "Convertir", "it": "Converti"},
    "OCR review": {
        "nl": "OCR-controle", "fr": "Vérification OCR", "de": "OCR-Prüfung", "es": "Revisión OCR",
        "it": "Revisione OCR"},
    "Document map": {
        "nl": "Documentoverzicht", "fr": "Plan du document", "de": "Dokumentübersicht", "es": "Mapa del documento",
        "it": "Mappa del documento"},
    "AI settings": {
        "nl": "AI-instellingen", "fr": "Paramètres IA", "de": "KI-Einstellungen", "es": "Ajustes de IA",
        "it": "Impostazioni IA"},
    "Settings": {"nl": "Instellingen", "fr": "Paramètres", "de": "Einstellungen", "es": "Ajustes",
                 "it": "Impostazioni"},
    "Help": {"nl": "Help", "fr": "Aide", "de": "Hilfe", "es": "Ayuda", "it": "Aiuto"},
    "Dismiss": {"nl": "Sluiten", "fr": "Fermer", "de": "Schließen", "es": "Cerrar", "it": "Chiudi"},
    "Review now": {"nl": "Nu nakijken", "fr": "Vérifier maintenant", "de": "Jetzt prüfen", "es": "Revisar ahora",
                   "it": "Rivedi ora"},
    "1 word needs your decision: OCR wasn't sure how to read it.": {
        "nl": "1 woord wacht op je beslissing: de OCR wist niet zeker hoe het te lezen.",
        "fr": "1 mot attend votre décision : l'OCR n'était pas sûre de sa lecture.",
        "de": "1 Wort wartet auf Ihre Entscheidung: Die OCR war sich beim Lesen nicht sicher.",
        "es": "1 palabra espera tu decisión: el OCR no estaba seguro de cómo leerla.",
        "it": "1 parola attende la tua decisione: l'OCR non era sicuro di come leggerla."},
    "{n} words need your decision: OCR wasn't sure how to read them.": {
        "nl": "{n} woorden wachten op je beslissing: de OCR wist niet zeker hoe ze te lezen.",
        "fr": "{n} mots attendent votre décision : l'OCR n'était pas sûre de leur lecture.",
        "de": "{n} Wörter warten auf Ihre Entscheidung: Die OCR war sich beim Lesen nicht sicher.",
        "es": "{n} palabras esperan tu decisión: el OCR no estaba seguro de cómo leerlas.",
        "it": "{n} parole attendono la tua decisione: l'OCR non era sicuro di come leggerle."},

    # ---------------------------------------------------------------- convert tab
    "Preset": {"nl": "Voorinstelling", "fr": "Préréglage", "de": "Vorlage", "es": "Ajuste predefinido",
               "it": "Preimpostazione"},
    "Standard": {"nl": "Standaard", "fr": "Standard", "de": "Standard", "es": "Estándar", "it": "Standard"},
    "Spacious": {"nl": "Ruim", "fr": "Aéré", "de": "Großzügig", "es": "Espacioso", "it": "Arioso"},
    "High Readability": {"nl": "Extra leesbaar", "fr": "Lisibilité maximale", "de": "Hohe Lesbarkeit",
                         "es": "Máxima legibilidad", "it": "Massima leggibilità"},
    "Compact print": {"nl": "Compact afdrukken", "fr": "Impression compacte", "de": "Kompakter Druck",
                      "es": "Impresión compacta", "it": "Stampa compatta"},
    "My Settings": {"nl": "Mijn instellingen", "fr": "Mes réglages", "de": "Meine Einstellungen",
                    "es": "Mis ajustes", "it": "Le mie impostazioni"},
    "Presets are formatting configurations only. They are not medical treatments and may not suit every reader "
    "- adjust any setting to what works for you.": {
        "nl": "Voorinstellingen zijn alleen opmaakinstellingen. Het zijn geen medische behandelingen en ze passen "
              "niet bij iedere lezer - pas elke instelling aan zoals het voor jou werkt.",
        "fr": "Les préréglages ne sont que des mises en forme. Ce ne sont pas des traitements médicaux et ils ne "
              "conviennent pas à tous les lecteurs - ajustez chaque réglage selon ce qui vous convient.",
        "de": "Vorlagen sind nur Formatierungen. Sie sind keine medizinische Behandlung und passen nicht zu jedem "
              "Leser - passen Sie jede Einstellung so an, wie es für Sie funktioniert.",
        "es": "Los ajustes predefinidos son solo formatos. No son tratamientos médicos y pueden no servir a todos "
              "los lectores: ajusta cada opción a lo que te funcione.",
        "it": "Le preimpostazioni sono solo formati. Non sono trattamenti medici e potrebbero non andare bene per "
              "ogni lettore: regola ogni impostazione come preferisci."},
    "Document language": {"nl": "Taal van het document", "fr": "Langue du document", "de": "Dokumentsprache",
                          "es": "Idioma del documento", "it": "Lingua del documento"},
    "Detect automatically": {"nl": "Automatisch herkennen", "fr": "Détecter automatiquement",
                             "de": "Automatisch erkennen", "es": "Detectar automáticamente",
                             "it": "Rileva automaticamente"},
    "Detect automatically (found: {language})": {
        "nl": "Automatisch herkennen (gevonden: {language})",
        "fr": "Détecter automatiquement (trouvé : {language})",
        "de": "Automatisch erkennen (erkannt: {language})",
        "es": "Detectar automáticamente (detectado: {language})",
        "it": "Rileva automaticamente (rilevato: {language})"},
    "Detected from the text of each PDF. Choose a language if the guess is wrong: it sets the dictionary for OCR, "
    "spelling fixes and rejoining split words.": {
        "nl": "Wordt herkend aan de tekst van elke pdf. Kies een taal als de gok fout is: die bepaalt het "
              "woordenboek voor OCR, spellingcorrecties en het samenvoegen van afgebroken woorden.",
        "fr": "Détectée à partir du texte de chaque PDF. Choisissez une langue si la détection se trompe : elle "
              "détermine le dictionnaire pour l'OCR, les corrections et la reconstitution des mots coupés.",
        "de": "Wird am Text jedes PDFs erkannt. Wählen Sie eine Sprache, falls die Erkennung falsch ist: Sie "
              "bestimmt das Wörterbuch für OCR, Korrekturen und das Zusammenfügen getrennter Wörter.",
        "es": "Se detecta a partir del texto de cada PDF. Elige un idioma si la detección falla: define el "
              "diccionario para el OCR, las correcciones y la unión de palabras cortadas.",
        "it": "Rilevata dal testo di ogni PDF. Scegli una lingua se il rilevamento è sbagliato: determina il "
              "dizionario per l'OCR, le correzioni e la ricomposizione delle parole divise."},
    "English": {"nl": "Engels", "fr": "anglais", "de": "Englisch", "es": "inglés", "it": "inglese"},
    "Dutch": {"nl": "Nederlands", "fr": "néerlandais", "de": "Niederländisch", "es": "neerlandés",
              "it": "olandese"},
    "German": {"nl": "Duits", "fr": "allemand", "de": "Deutsch", "es": "alemán", "it": "tedesco"},
    "French": {"nl": "Frans", "fr": "français", "de": "Französisch", "es": "francés", "it": "francese"},
    "Spanish": {"nl": "Spaans", "fr": "espagnol", "de": "Spanisch", "es": "español", "it": "spagnolo"},
    "Italian": {"nl": "Italiaans", "fr": "italien", "de": "Italienisch", "es": "italiano", "it": "italiano"},
    "Portuguese": {"nl": "Portugees", "fr": "portugais", "de": "Portugiesisch", "es": "portugués",
                   "it": "portoghese"},
    "Text": {"nl": "Tekst", "fr": "Texte", "de": "Text", "es": "Texto", "it": "Testo"},
    "Font": {"nl": "Lettertype", "fr": "Police", "de": "Schriftart", "es": "Fuente", "it": "Carattere"},
    "Font size": {"nl": "Lettergrootte", "fr": "Taille du texte", "de": "Schriftgröße", "es": "Tamaño de letra",
                  "it": "Dimensione del testo"},
    "Line spacing": {"nl": "Regelafstand", "fr": "Interligne", "de": "Zeilenabstand", "es": "Interlineado",
                     "it": "Interlinea"},
    "Paragraph spacing": {"nl": "Ruimte tussen alinea's", "fr": "Espace entre paragraphes",
                          "de": "Absatzabstand", "es": "Espacio entre párrafos", "it": "Spazio tra paragrafi"},
    "Letter spacing": {"nl": "Letterafstand", "fr": "Espacement des lettres", "de": "Zeichenabstand",
                       "es": "Espaciado entre letras", "it": "Spaziatura tra lettere"},
    "Word spacing": {"nl": "Woordafstand", "fr": "Espacement des mots", "de": "Wortabstand",
                     "es": "Espaciado entre palabras", "it": "Spaziatura tra parole"},
    "Alignment": {"nl": "Uitlijning", "fr": "Alignement", "de": "Ausrichtung", "es": "Alineación",
                  "it": "Allineamento"},
    "Left (recommended)": {"nl": "Links (aanbevolen)", "fr": "À gauche (recommandé)", "de": "Links (empfohlen)",
                           "es": "Izquierda (recomendado)", "it": "A sinistra (consigliato)"},
    "Centre": {"nl": "Gecentreerd", "fr": "Centré", "de": "Zentriert", "es": "Centrado", "it": "Centrato"},
    "Justified": {"nl": "Uitgevuld", "fr": "Justifié", "de": "Blocksatz", "es": "Justificado",
                  "it": "Giustificato"},
    "Page": {"nl": "Pagina", "fr": "Page", "de": "Seite", "es": "Página", "it": "Pagina"},
    "Reading width": {"nl": "Leesbreedte", "fr": "Largeur de lecture", "de": "Lesebreite",
                      "es": "Ancho de lectura", "it": "Larghezza di lettura"},
    "Top margin": {"nl": "Bovenmarge", "fr": "Marge du haut", "de": "Rand oben", "es": "Margen superior",
                   "it": "Margine superiore"},
    "Bottom margin": {"nl": "Ondermarge", "fr": "Marge du bas", "de": "Rand unten", "es": "Margen inferior",
                      "it": "Margine inferiore"},
    "Left margin": {"nl": "Linkermarge", "fr": "Marge de gauche", "de": "Rand links", "es": "Margen izquierdo",
                    "it": "Margine sinistro"},
    "Right margin": {"nl": "Rechtermarge", "fr": "Marge de droite", "de": "Rand rechts", "es": "Margen derecho",
                     "it": "Margine destro"},
    "Page colour (screen PDF)": {"nl": "Paginakleur (pdf voor scherm)", "fr": "Couleur de page (PDF écran)",
                                 "de": "Seitenfarbe (Bildschirm-PDF)", "es": "Color de página (PDF de pantalla)",
                                 "it": "Colore della pagina (PDF per schermo)"},
    "Cream": {"nl": "Crème", "fr": "Crème", "de": "Creme", "es": "Crema", "it": "Crema"},
    "Light blue": {"nl": "Lichtblauw", "fr": "Bleu clair", "de": "Hellblau", "es": "Azul claro",
                   "it": "Azzurro"},
    "White": {"nl": "Wit", "fr": "Blanc", "de": "Weiß", "es": "Blanco", "it": "Bianco"},
    "Boxes for abstract & quotes, lines under headings": {
        "nl": "Kaders rond samenvatting en citaten, lijnen onder koppen",
        "fr": "Encadrés pour le résumé et les citations, traits sous les titres",
        "de": "Kästen für Zusammenfassung und Zitate, Linien unter Überschriften",
        "es": "Recuadros para el resumen y las citas, líneas bajo los títulos",
        "it": "Riquadri per abstract e citazioni, linee sotto i titoli"},
    "Ink-saving mode (no backgrounds or decorations)": {
        "nl": "Inktbesparend (geen achtergronden of versiering)",
        "fr": "Mode économie d'encre (sans fonds ni décorations)",
        "de": "Tintensparmodus (keine Hintergründe oder Verzierungen)",
        "es": "Ahorro de tinta (sin fondos ni decoraciones)",
        "it": "Risparmio inchiostro (niente sfondi o decorazioni)"},
    "Page numbers": {"nl": "Paginanummers", "fr": "Numéros de page", "de": "Seitenzahlen",
                     "es": "Números de página", "it": "Numeri di pagina"},
    "Contents page (document map)": {"nl": "Inhoudsopgave (documentoverzicht)",
                                     "fr": "Table des matières (plan du document)",
                                     "de": "Inhaltsverzeichnis (Dokumentübersicht)",
                                     "es": "Índice (mapa del documento)", "it": "Indice (mappa del documento)"},
    "Bold start of words": {"nl": "Vet begin van woorden", "fr": "Début des mots en gras",
                            "de": "Wortanfänge fett", "es": "Inicio de palabras en negrita",
                            "it": "Inizio delle parole in grassetto"},
    "Bold the first part of each word": {"nl": "Het eerste deel van elk woord vet", "fr": "Mettre en gras le "
                                         "début de chaque mot", "de": "Den Anfang jedes Wortes fett drucken",
                                         "es": "Poner en negrita el inicio de cada palabra",
                                         "it": "Grassetto sulla prima parte di ogni parola"},
    "Changes only how words look, never the text": {
        "nl": "Verandert alleen hoe woorden eruitzien, nooit de tekst",
        "fr": "Change seulement l'aspect des mots, jamais le texte",
        "de": "Ändert nur das Aussehen der Wörter, nie den Text",
        "es": "Solo cambia el aspecto de las palabras, nunca el texto",
        "it": "Cambia solo l'aspetto delle parole, mai il testo"},
    "How much": {"nl": "Hoeveel", "fr": "Quelle part", "de": "Wie viel", "es": "Cuánto", "it": "Quanto"},
    "First letter": {"nl": "Eerste letter", "fr": "Première lettre", "de": "Erster Buchstabe",
                     "es": "Primera letra", "it": "Prima lettera"},
    "First 25%": {"nl": "Eerste 25%", "fr": "Premiers 25 %", "de": "Erste 25 %", "es": "Primer 25 %",
                  "it": "Primo 25%"},
    "First 40%": {"nl": "Eerste 40%", "fr": "Premiers 40 %", "de": "Erste 40 %", "es": "Primer 40 %",
                  "it": "Primo 40%"},
    "Automatic": {"nl": "Automatisch", "fr": "Automatique", "de": "Automatisch", "es": "Automático",
                  "it": "Automatico"},
    "Also in references and citations": {"nl": "Ook in bronvermeldingen en verwijzingen",
                                         "fr": "Aussi dans les références et citations",
                                         "de": "Auch in Literaturangaben und Zitaten",
                                         "es": "También en referencias y citas",
                                         "it": "Anche in bibliografia e citazioni"},
    "Structure": {"nl": "Structuur", "fr": "Structure", "de": "Struktur", "es": "Estructura", "it": "Struttura"},
    "Move footnotes to the end": {"nl": "Voetnoten naar het einde verplaatsen", "fr": "Déplacer les notes de "
                                  "bas de page à la fin", "de": "Fußnoten ans Ende verschieben",
                                  "es": "Mover las notas al pie al final", "it": "Sposta le note a piè di "
                                  "pagina alla fine"},
    "Move author-year citations to numbers [1]": {
        "nl": "Auteur-jaarverwijzingen omzetten naar nummers [1]",
        "fr": "Remplacer les citations auteur-année par des numéros [1]",
        "de": "Autor-Jahr-Zitate durch Nummern [1] ersetzen",
        "es": "Cambiar las citas autor-año por números [1]",
        "it": "Sostituisci le citazioni autore-anno con numeri [1]"},
    "Automated citation detection can make mistakes. Original citation text is kept.": {
        "nl": "Automatische herkenning van verwijzingen kan fouten maken. De originele tekst blijft bewaard.",
        "fr": "La détection automatique des citations peut se tromper. Le texte d'origine est conservé.",
        "de": "Die automatische Zitaterkennung kann Fehler machen. Der Originaltext bleibt erhalten.",
        "es": "La detección automática de citas puede equivocarse. Se conserva el texto original.",
        "it": "Il rilevamento automatico delle citazioni può sbagliare. Il testo originale viene conservato."},
    "Automated citation detection can make mistakes; the original citation text is always kept in the list.": {
        "nl": "Automatische herkenning van verwijzingen kan fouten maken; de originele tekst staat altijd in de "
              "lijst.",
        "fr": "La détection automatique des citations peut se tromper ; le texte d'origine est toujours conservé "
              "dans la liste.",
        "de": "Die automatische Zitaterkennung kann Fehler machen; der Originaltext bleibt immer in der Liste.",
        "es": "La detección automática de citas puede equivocarse; el texto original siempre se conserva en la "
              "lista.",
        "it": "Il rilevamento automatico delle citazioni può sbagliare; il testo originale resta sempre "
              "nell'elenco."},
    "Hide running headers, footers and page numbers": {
        "nl": "Kop- en voetteksten en paginanummers verbergen",
        "fr": "Masquer les en-têtes, pieds de page et numéros de page",
        "de": "Kopf- und Fußzeilen sowie Seitenzahlen ausblenden",
        "es": "Ocultar encabezados, pies de página y números de página",
        "it": "Nascondi intestazioni, piè di pagina e numeri di pagina"},
    "Show logos and decorative images": {"nl": "Logo's en decoratieve afbeeldingen tonen",
                                         "fr": "Afficher les logos et images décoratives",
                                         "de": "Logos und dekorative Bilder anzeigen",
                                         "es": "Mostrar logotipos e imágenes decorativas",
                                         "it": "Mostra loghi e immagini decorative"},
    "Tables": {"nl": "Tabellen", "fr": "Tableaux", "de": "Tabellen", "es": "Tablas", "it": "Tabelle"},
    "Rebuild as tables when reliable": {"nl": "Als tabel opnieuw opbouwen als dat betrouwbaar kan",
                                        "fr": "Reconstruire en tableaux quand c'est fiable",
                                        "de": "Als Tabelle neu aufbauen, wenn zuverlässig",
                                        "es": "Reconstruir como tablas cuando sea fiable",
                                        "it": "Ricostruisci come tabelle quando è affidabile"},
    "Always keep as picture": {"nl": "Altijd als afbeelding houden", "fr": "Toujours garder en image",
                               "de": "Immer als Bild behalten", "es": "Mantener siempre como imagen",
                               "it": "Mantieni sempre come immagine"},
    "Add an 'About this version' note at the end": {
        "nl": "Een notitie 'Over deze versie' aan het einde toevoegen",
        "fr": "Ajouter une note « À propos de cette version » à la fin",
        "de": "Einen Hinweis „Über diese Fassung“ am Ende hinzufügen",
        "es": "Añadir una nota «Acerca de esta versión» al final",
        "it": "Aggiungi una nota «Informazioni su questa versione» alla fine"},
    "Scanned documents (OCR)": {"nl": "Gescande documenten (OCR)", "fr": "Documents numérisés (OCR)",
                                "de": "Gescannte Dokumente (OCR)", "es": "Documentos escaneados (OCR)",
                                "it": "Documenti scansionati (OCR)"},
    "OCR correction": {"nl": "OCR-correctie", "fr": "Correction OCR", "de": "OCR-Korrektur",
                       "es": "Corrección OCR", "it": "Correzione OCR"},
    "Review uncertain corrections": {"nl": "Onzekere correcties zelf nakijken",
                                     "fr": "Vérifier les corrections incertaines",
                                     "de": "Unsichere Korrekturen prüfen",
                                     "es": "Revisar las correcciones dudosas",
                                     "it": "Rivedi le correzioni incerte"},
    "Automatic (high confidence only)": {"nl": "Automatisch (alleen bij grote zekerheid)",
                                         "fr": "Automatique (forte confiance seulement)",
                                         "de": "Automatisch (nur bei hoher Sicherheit)",
                                         "es": "Automático (solo con alta confianza)",
                                         "it": "Automatica (solo con alta affidabilità)"},
    "Off": {"nl": "Uit", "fr": "Désactivée", "de": "Aus", "es": "Desactivada", "it": "Disattivata"},
    "Split two-page book scans into single pages": {
        "nl": "Scans van twee boekpagina's splitsen in losse pagina's",
        "fr": "Séparer les scans de doubles pages en pages simples",
        "de": "Doppelseitige Buchscans in einzelne Seiten teilen",
        "es": "Dividir los escaneos de doble página en páginas sueltas",
        "it": "Dividi le scansioni di due pagine in pagine singole"},
    "Text of scanned pages": {"nl": "Tekst van gescande pagina's", "fr": "Texte des pages numérisées",
                              "de": "Text gescannter Seiten", "es": "Texto de las páginas escaneadas",
                              "it": "Testo delle pagine scansionate"},
    "Clean up and read the scan (best quality)": {
        "nl": "De scan opschonen en lezen (beste kwaliteit)",
        "fr": "Nettoyer et lire le scan (meilleure qualité)",
        "de": "Scan bereinigen und lesen (beste Qualität)",
        "es": "Limpiar y leer el escaneo (mejor calidad)",
        "it": "Pulisci e leggi la scansione (qualità migliore)"},
    "Use the scanner's own text layer (faster)": {
        "nl": "De tekstlaag van de scanner gebruiken (sneller)",
        "fr": "Utiliser la couche texte du scanner (plus rapide)",
        "de": "Die Textebene des Scanners verwenden (schneller)",
        "es": "Usar la capa de texto del escáner (más rápido)",
        "it": "Usa il livello di testo dello scanner (più veloce)"},
    "Scans are straightened, gutter shadows and dark borders are removed, and two-page spreads are split before "
    "the text is read.": {
        "nl": "Scans worden rechtgezet, schaduwen in de rugmarge en donkere randen verdwijnen, en dubbele pagina's "
              "worden gesplitst voordat de tekst gelezen wordt.",
        "fr": "Les scans sont redressés, les ombres de reliure et les bords sombres sont supprimés, et les doubles "
              "pages sont séparées avant la lecture du texte.",
        "de": "Scans werden gerade gerichtet, Schatten im Bund und dunkle Ränder entfernt und Doppelseiten "
              "geteilt, bevor der Text gelesen wird.",
        "es": "Los escaneos se enderezan, se eliminan las sombras del lomo y los bordes oscuros, y las dobles "
              "páginas se dividen antes de leer el texto.",
        "it": "Le scansioni vengono raddrizzate, le ombre della rilegatura e i bordi scuri rimossi e le doppie "
              "pagine divise prima di leggere il testo."},
    "OCR: Tesseract found": {"nl": "OCR: Tesseract gevonden", "fr": "OCR : Tesseract trouvé",
                             "de": "OCR: Tesseract gefunden", "es": "OCR: Tesseract encontrado",
                             "it": "OCR: Tesseract trovato"},
    "OCR: not available - install Tesseract to convert scanned PDFs. Scans that already contain a text layer can "
    "still be converted.": {
        "nl": "OCR: niet beschikbaar - installeer Tesseract om gescande pdf's om te zetten. Scans met een "
              "tekstlaag kunnen nog wel omgezet worden.",
        "fr": "OCR : indisponible - installez Tesseract pour convertir les PDF numérisés. Les scans qui ont déjà "
              "une couche texte restent convertibles.",
        "de": "OCR: nicht verfügbar - installieren Sie Tesseract, um gescannte PDFs umzuwandeln. Scans mit "
              "Textebene lassen sich trotzdem umwandeln.",
        "es": "OCR: no disponible; instala Tesseract para convertir PDF escaneados. Los escaneos que ya tienen "
              "capa de texto se pueden convertir igualmente.",
        "it": "OCR: non disponibile - installa Tesseract per convertire i PDF scansionati. Le scansioni che hanno "
              "già un livello di testo si possono comunque convertire."},
    "Pages to convert": {"nl": "Pagina's om om te zetten", "fr": "Pages à convertir",
                         "de": "Umzuwandelnde Seiten", "es": "Páginas que convertir", "it": "Pagine da convertire"},
    "From page": {"nl": "Van pagina", "fr": "De la page", "de": "Von Seite", "es": "Desde la página",
                  "it": "Dalla pagina"},
    "To page": {"nl": "Tot pagina", "fr": "À la page", "de": "Bis Seite", "es": "Hasta la página",
                "it": "Alla pagina"},
    "Apply": {"nl": "Toepassen", "fr": "Appliquer", "de": "Anwenden", "es": "Aplicar", "it": "Applica"},
    "Leave empty to convert all pages. Useful when a PDF starts with the end of another article.": {
        "nl": "Leeg laten om alle pagina's om te zetten. Handig als een pdf begint met het einde van een ander "
              "artikel.",
        "fr": "Laissez vide pour convertir toutes les pages. Utile quand un PDF commence par la fin d'un autre "
              "article.",
        "de": "Leer lassen, um alle Seiten umzuwandeln. Nützlich, wenn ein PDF mit dem Ende eines anderen "
              "Artikels beginnt.",
        "es": "Déjalo vacío para convertir todas las páginas. Útil cuando un PDF empieza con el final de otro "
              "artículo.",
        "it": "Lascia vuoto per convertire tutte le pagine. Utile quando un PDF inizia con la fine di un altro "
              "articolo."},
    "Save as My Settings": {"nl": "Opslaan als Mijn instellingen", "fr": "Enregistrer dans Mes réglages",
                            "de": "Als Meine Einstellungen speichern", "es": "Guardar como Mis ajustes",
                            "it": "Salva come Le mie impostazioni"},
    "Restore defaults": {"nl": "Standaardinstellingen herstellen", "fr": "Rétablir les réglages par défaut",
                         "de": "Standard wiederherstellen", "es": "Restaurar valores predeterminados",
                         "it": "Ripristina predefiniti"},
    "Original page": {"nl": "Originele pagina", "fr": "Page d'origine", "de": "Originalseite",
                      "es": "Página original", "it": "Pagina originale"},
    "Converted page": {"nl": "Omgezette pagina", "fr": "Page convertie", "de": "Umgewandelte Seite",
                       "es": "Página convertida", "it": "Pagina convertita"},
    "Original": {"nl": "Origineel", "fr": "Original", "de": "Original", "es": "Original", "it": "Originale"},
    "Converted": {"nl": "Omgezet", "fr": "Converti", "de": "Umgewandelt", "es": "Convertido", "it": "Convertito"},
    "Both": {"nl": "Beide", "fr": "Les deux", "de": "Beide", "es": "Ambos", "it": "Entrambi"},
    "Previous page": {"nl": "Vorige pagina", "fr": "Page précédente", "de": "Vorherige Seite",
                      "es": "Página anterior", "it": "Pagina precedente"},
    "Next page": {"nl": "Volgende pagina", "fr": "Page suivante", "de": "Nächste Seite", "es": "Página siguiente",
                  "it": "Pagina successiva"},
    "Export:": {"nl": "Exporteren:", "fr": "Exporter :", "de": "Exportieren:", "es": "Exportar:",
                "it": "Esporta:"},
    "Save as {format}": {"nl": "Opslaan als {format}", "fr": "Enregistrer en {format}",
                         "de": "Als {format} speichern", "es": "Guardar como {format}", "it": "Salva come {format}"},
    "PDF": {"nl": "PDF", "fr": "PDF", "de": "PDF", "es": "PDF", "it": "PDF"},
    "Printable PDF": {"nl": "PDF om af te drukken", "fr": "PDF à imprimer", "de": "Druck-PDF",
                      "es": "PDF para imprimir", "it": "PDF da stampare"},
    "Word (DOCX)": {"nl": "Word (DOCX)", "fr": "Word (DOCX)", "de": "Word (DOCX)", "es": "Word (DOCX)",
                    "it": "Word (DOCX)"},
    "Plain text": {"nl": "Platte tekst", "fr": "Texte brut", "de": "Reiner Text", "es": "Texto sin formato",
                   "it": "Testo semplice"},
    "Markdown": {"nl": "Markdown", "fr": "Markdown", "de": "Markdown", "es": "Markdown", "it": "Markdown"},

    # ---------------------------------------------------------------- review tab
    "OCR corrections": {"nl": "OCR-correcties", "fr": "Corrections OCR", "de": "OCR-Korrekturen",
                        "es": "Correcciones OCR", "it": "Correzioni OCR"},
    "Corrections use a local dictionary. The original OCR text is kept, so every correction can be undone.": {
        "nl": "Correcties gebruiken een lokaal woordenboek. De originele OCR-tekst blijft bewaard, dus elke "
              "correctie kan ongedaan gemaakt worden.",
        "fr": "Les corrections utilisent un dictionnaire local. Le texte OCR d'origine est conservé : chaque "
              "correction peut être annulée.",
        "de": "Korrekturen nutzen ein lokales Wörterbuch. Der ursprüngliche OCR-Text bleibt erhalten, jede "
              "Korrektur lässt sich rückgängig machen.",
        "es": "Las correcciones usan un diccionario local. Se conserva el texto OCR original, así que cada "
              "corrección se puede deshacer.",
        "it": "Le correzioni usano un dizionario locale. Il testo OCR originale viene conservato, quindi ogni "
              "correzione si può annullare."},
    "No scanned document loaded.": {"nl": "Geen gescand document geopend.", "fr": "Aucun document numérisé "
                                    "ouvert.", "de": "Kein gescanntes Dokument geöffnet.",
                                    "es": "No hay ningún documento escaneado abierto.",
                                    "it": "Nessun documento scansionato aperto."},
    "No OCR was needed for this document.": {"nl": "Voor dit document was geen OCR nodig.",
                                             "fr": "Aucune OCR n'a été nécessaire pour ce document.",
                                             "de": "Für dieses Dokument war keine OCR nötig.",
                                             "es": "Este documento no necesitó OCR.",
                                             "it": "Per questo documento l'OCR non è servito."},
    "{done} correction(s) applied, {pending} waiting for your review. Mode: {mode}.": {
        "nl": "{done} correctie(s) toegepast, {pending} wachten op jouw controle. Modus: {mode}.",
        "fr": "{done} correction(s) appliquée(s), {pending} en attente de votre vérification. Mode : {mode}.",
        "de": "{done} Korrektur(en) angewendet, {pending} warten auf Ihre Prüfung. Modus: {mode}.",
        "es": "{done} corrección(es) aplicada(s), {pending} pendiente(s) de tu revisión. Modo: {mode}.",
        "it": "{done} correzione/i applicata/e, {pending} in attesa della tua revisione. Modalità: {mode}."},
    "Undo all corrections": {"nl": "Alle correcties ongedaan maken", "fr": "Annuler toutes les corrections",
                             "de": "Alle Korrekturen rückgängig machen", "es": "Deshacer todas las correcciones",
                             "it": "Annulla tutte le correzioni"},
    "My dictionary (names, technical terms, abbreviations)": {
        "nl": "Mijn woordenboek (namen, vaktermen, afkortingen)",
        "fr": "Mon dictionnaire (noms, termes techniques, abréviations)",
        "de": "Mein Wörterbuch (Namen, Fachbegriffe, Abkürzungen)",
        "es": "Mi diccionario (nombres, términos técnicos, abreviaturas)",
        "it": "Il mio dizionario (nomi, termini tecnici, abbreviazioni)"},
    "Add a word to your dictionary": {"nl": "Een woord aan je woordenboek toevoegen",
                                      "fr": "Ajouter un mot à votre dictionnaire",
                                      "de": "Ein Wort zum Wörterbuch hinzufügen",
                                      "es": "Añadir una palabra a tu diccionario",
                                      "it": "Aggiungi una parola al dizionario"},
    "Add": {"nl": "Toevoegen", "fr": "Ajouter", "de": "Hinzufügen", "es": "Añadir", "it": "Aggiungi"},
    "(none yet)": {"nl": "(nog geen)", "fr": "(aucun pour l'instant)", "de": "(noch keine)", "es": "(ninguna aún)",
                   "it": "(ancora nessuna)"},
    "Waiting for review": {"nl": "Wacht op controle", "fr": "En attente de vérification", "de": "Wartet auf "
                           "Prüfung", "es": "Pendiente de revisión", "it": "In attesa di revisione"},
    "Applied automatically": {"nl": "Automatisch toegepast", "fr": "Appliquée automatiquement",
                              "de": "Automatisch angewendet", "es": "Aplicada automáticamente",
                              "it": "Applicata automaticamente"},
    "Accepted": {"nl": "Aanvaard", "fr": "Acceptée", "de": "Angenommen", "es": "Aceptada", "it": "Accettata"},
    "Rejected (original kept)": {"nl": "Geweigerd (origineel behouden)", "fr": "Refusée (original conservé)",
                                 "de": "Abgelehnt (Original bleibt)", "es": "Rechazada (se mantiene el original)",
                                 "it": "Rifiutata (originale mantenuto)"},
    "Accept": {"nl": "Aanvaarden", "fr": "Accepter", "de": "Annehmen", "es": "Aceptar", "it": "Accetta"},
    "Reject": {"nl": "Weigeren", "fr": "Refuser", "de": "Ablehnen", "es": "Rechazar", "it": "Rifiuta"},
    "Undo": {"nl": "Ongedaan maken", "fr": "Annuler", "de": "Rückgängig", "es": "Deshacer", "it": "Annulla"},
    "'{word}' is correct - add to dictionary": {
        "nl": "'{word}' is juist - toevoegen aan woordenboek",
        "fr": "« {word} » est correct - ajouter au dictionnaire",
        "de": "„{word}“ ist richtig - zum Wörterbuch hinzufügen",
        "es": "«{word}» es correcto: añadir al diccionario",
        "it": "«{word}» è corretto - aggiungi al dizionario"},
    "suggested": {"nl": "voorgesteld", "fr": "proposé", "de": "vorgeschlagen", "es": "sugerido", "it": "suggerito"},
    "Confidence {pct}%": {"nl": "Zekerheid {pct}%", "fr": "Confiance {pct} %", "de": "Sicherheit {pct} %",
                          "es": "Confianza {pct} %", "it": "Affidabilità {pct}%"},
    "Edit": {"nl": "Bewerken", "fr": "Modifier", "de": "Bearbeiten", "es": "Editar", "it": "Modifica"},
    "Type the text yourself": {"nl": "Typ de tekst zelf", "fr": "Saisir le texte vous-même",
                               "de": "Text selbst eingeben", "es": "Escribe el texto tú mismo",
                               "it": "Scrivi tu il testo"},
    "Correct the text": {"nl": "Tekst verbeteren", "fr": "Corriger le texte", "de": "Text korrigieren",
                         "es": "Corregir el texto", "it": "Correggi il testo"},
    "Type the sentence as it should read. Only the words you change are replaced; the scan itself is not changed "
    "and you can undo this.": {
        "nl": "Typ de zin zoals hij hoort te zijn. Alleen de woorden die je verandert worden vervangen; de scan zelf "
              "verandert niet en je kunt dit ongedaan maken.",
        "fr": "Saisissez la phrase telle qu'elle devrait être. Seuls les mots modifiés sont remplacés ; le scan "
              "lui-même n'est pas modifié et vous pouvez annuler.",
        "de": "Geben Sie den Satz so ein, wie er lauten soll. Nur die geänderten Wörter werden ersetzt; der Scan "
              "selbst bleibt unverändert und Sie können das rückgängig machen.",
        "es": "Escribe la frase como debería ser. Solo se sustituyen las palabras que cambies; el escaneo no se "
              "modifica y puedes deshacerlo.",
        "it": "Scrivi la frase come dovrebbe essere. Vengono sostituite solo le parole che cambi; la scansione non "
              "viene modificata e puoi annullare."},
    "Cancel": {"nl": "Annuleren", "fr": "Annuler", "de": "Abbrechen", "es": "Cancelar", "it": "Annulla"},
    "Save": {"nl": "Opslaan", "fr": "Enregistrer", "de": "Speichern", "es": "Guardar", "it": "Salva"},
    "Nothing was changed.": {"nl": "Er is niets veranderd.", "fr": "Rien n'a été modifié.",
                             "de": "Es wurde nichts geändert.", "es": "No se ha cambiado nada.",
                             "it": "Non è stato cambiato nulla."},
    "Your correction was saved. You can undo it at any time.": {
        "nl": "Je verbetering is opgeslagen. Je kunt ze altijd ongedaan maken.",
        "fr": "Votre correction est enregistrée. Vous pouvez l'annuler à tout moment.",
        "de": "Ihre Korrektur wurde gespeichert. Sie können sie jederzeit rückgängig machen.",
        "es": "Tu corrección se ha guardado. Puedes deshacerla cuando quieras.",
        "it": "La tua correzione è stata salvata. Puoi annullarla in qualsiasi momento."},
    "Your correction": {"nl": "Jouw verbetering", "fr": "Votre correction", "de": "Ihre Korrektur",
                        "es": "Tu corrección", "it": "La tua correzione"},
    "typed by you": {"nl": "door jou getypt", "fr": "saisi par vous", "de": "von Ihnen eingegeben",
                     "es": "escrito por ti", "it": "scritto da te"},
    "dictionary": {"nl": "woordenboek", "fr": "dictionnaire", "de": "Wörterbuch", "es": "diccionario",
                   "it": "dizionario"},
    "In the text:": {"nl": "In de tekst:", "fr": "Dans le texte :", "de": "Im Text:", "es": "En el texto:",
                     "it": "Nel testo:"},
    "'{word}' added to your dictionary.": {
        "nl": "'{word}' is toegevoegd aan je woordenboek.",
        "fr": "« {word} » a été ajouté à votre dictionnaire.",
        "de": "„{word}“ wurde zum Wörterbuch hinzugefügt.",
        "es": "«{word}» se ha añadido a tu diccionario.",
        "it": "«{word}» è stato aggiunto al dizionario."},

    # ---------------------------------------------------------------- map tab
    "Headings found in the document. Select one to show it in the preview. Nothing here is invented: only "
    "headings present in the original are listed.": {
        "nl": "Koppen die in het document gevonden zijn. Kies er een om die in het voorbeeld te tonen. Hier wordt "
              "niets verzonnen: alleen koppen uit het origineel staan in de lijst.",
        "fr": "Titres trouvés dans le document. Sélectionnez-en un pour l'afficher dans l'aperçu. Rien n'est "
              "inventé : seuls les titres présents dans l'original sont listés.",
        "de": "Im Dokument gefundene Überschriften. Wählen Sie eine aus, um sie in der Vorschau zu zeigen. Nichts "
              "wird erfunden: Nur Überschriften aus dem Original stehen hier.",
        "es": "Títulos encontrados en el documento. Selecciona uno para verlo en la vista previa. No se inventa "
              "nada: solo aparecen los títulos del original.",
        "it": "Titoli trovati nel documento. Selezionane uno per vederlo nell'anteprima. Qui non si inventa "
              "nulla: sono elencati solo i titoli presenti nell'originale."},
    "page {n}": {"nl": "pagina {n}", "fr": "page {n}", "de": "Seite {n}", "es": "página {n}", "it": "pagina {n}"},
    "No headings were detected.": {"nl": "Er zijn geen koppen gevonden.", "fr": "Aucun titre n'a été détecté.",
                                   "de": "Es wurden keine Überschriften erkannt.",
                                   "es": "No se detectaron títulos.", "it": "Non è stato rilevato alcun titolo."},

    # ---------------------------------------------------------------- AI tab
    "AI assistance (optional)": {"nl": "AI-hulp (optioneel)", "fr": "Assistance IA (facultative)",
                                 "de": "KI-Unterstützung (optional)", "es": "Ayuda de IA (opcional)",
                                 "it": "Assistenza IA (facoltativa)"},
    "The converter works fully without AI. AI is only asked about items local rules are unsure about, in small "
    "snippets, and answers are cached so nothing is sent twice.": {
        "nl": "De converter werkt volledig zonder AI. AI krijgt alleen vragen over twijfelgevallen, in kleine "
              "stukjes tekst, en antwoorden worden bewaard zodat niets twee keer verstuurd wordt.",
        "fr": "Le convertisseur fonctionne entièrement sans IA. L'IA n'est consultée que sur les cas douteux, par "
              "petits extraits, et les réponses sont gardées pour ne rien envoyer deux fois.",
        "de": "Der Konverter funktioniert vollständig ohne KI. Die KI wird nur zu unsicheren Stellen in kleinen "
              "Ausschnitten befragt; Antworten werden gespeichert, damit nichts zweimal gesendet wird.",
        "es": "El conversor funciona por completo sin IA. Solo se consulta a la IA sobre casos dudosos, en "
              "fragmentos pequeños, y las respuestas se guardan para no enviar nada dos veces.",
        "it": "Il convertitore funziona completamente senza IA. L'IA viene interpellata solo sui casi incerti, in "
              "piccoli estratti, e le risposte vengono salvate per non inviare nulla due volte."},
    "Local-only - no document content leaves this device": {
        "nl": "Alleen lokaal - er verlaat geen documentinhoud dit apparaat",
        "fr": "Local uniquement - aucun contenu ne quitte cet appareil",
        "de": "Nur lokal - kein Dokumentinhalt verlässt dieses Gerät",
        "es": "Solo local: ningún contenido sale de este dispositivo",
        "it": "Solo locale - nessun contenuto lascia questo dispositivo"},
    "AI-assisted - selected snippets may be sent to your AI provider": {
        "nl": "Met AI-hulp - gekozen stukjes tekst kunnen naar je AI-aanbieder gaan",
        "fr": "Assisté par IA - certains extraits peuvent être envoyés à votre fournisseur d'IA",
        "de": "KI-gestützt - ausgewählte Ausschnitte können an Ihren KI-Anbieter gehen",
        "es": "Con ayuda de IA: algunos fragmentos pueden enviarse a tu proveedor de IA",
        "it": "Con assistenza IA - alcuni estratti possono essere inviati al tuo fornitore di IA"},
    "Provider": {"nl": "Aanbieder", "fr": "Fournisseur", "de": "Anbieter", "es": "Proveedor", "it": "Fornitore"},
    "Model": {"nl": "Model", "fr": "Modèle", "de": "Modell", "es": "Modelo", "it": "Modello"},
    "API key": {"nl": "API-sleutel", "fr": "Clé API", "de": "API-Schlüssel", "es": "Clave API", "it": "Chiave API"},
    "Save key": {"nl": "Sleutel opslaan", "fr": "Enregistrer la clé", "de": "Schlüssel speichern",
                 "es": "Guardar clave", "it": "Salva chiave"},
    "Remove key": {"nl": "Sleutel verwijderen", "fr": "Supprimer la clé", "de": "Schlüssel entfernen",
                   "es": "Eliminar clave", "it": "Rimuovi chiave"},
    "A key is saved ({where}).": {"nl": "Er is een sleutel bewaard ({where}).",
                                  "fr": "Une clé est enregistrée ({where}).",
                                  "de": "Ein Schlüssel ist gespeichert ({where}).",
                                  "es": "Hay una clave guardada ({where}).", "it": "È salvata una chiave ({where})."},
    "system keychain": {"nl": "sleutelhanger van het systeem", "fr": "trousseau du système",
                        "de": "Schlüsselbund des Systems", "es": "llavero del sistema",
                        "it": "portachiavi di sistema"},
    "private file on this device": {"nl": "privébestand op dit apparaat", "fr": "fichier privé sur cet appareil",
                                    "de": "private Datei auf diesem Gerät", "es": "archivo privado en este "
                                    "dispositivo", "it": "file privato su questo dispositivo"},
    "No key saved for this provider.": {"nl": "Geen sleutel bewaard voor deze aanbieder.",
                                        "fr": "Aucune clé enregistrée pour ce fournisseur.",
                                        "de": "Für diesen Anbieter ist kein Schlüssel gespeichert.",
                                        "es": "No hay clave guardada para este proveedor.",
                                        "it": "Nessuna chiave salvata per questo fornitore."},
    "Your AI provider may charge you for API usage.": {
        "nl": "Je AI-aanbieder kan kosten aanrekenen voor API-gebruik.",
        "fr": "Votre fournisseur d'IA peut facturer l'utilisation de l'API.",
        "de": "Ihr KI-Anbieter kann die API-Nutzung berechnen.",
        "es": "Tu proveedor de IA puede cobrar por el uso de la API.",
        "it": "Il tuo fornitore di IA può addebitare l'uso dell'API."},
    "Use AI for:": {"nl": "AI gebruiken voor:", "fr": "Utiliser l'IA pour :", "de": "KI verwenden für:",
                    "es": "Usar IA para:", "it": "Usa l'IA per:"},
    "Uncertain citations": {"nl": "Twijfelachtige verwijzingen", "fr": "Citations incertaines",
                            "de": "Unsichere Zitate", "es": "Citas dudosas", "it": "Citazioni incerte"},
    "Uncertain OCR words": {"nl": "Twijfelachtige OCR-woorden", "fr": "Mots OCR incertains",
                            "de": "Unsichere OCR-Wörter", "es": "Palabras OCR dudosas", "it": "Parole OCR incerte"},
    "Ask AI about uncertain items now": {"nl": "AI nu over de twijfelgevallen vragen",
                                         "fr": "Interroger l'IA sur les cas incertains",
                                         "de": "KI jetzt zu unsicheren Stellen befragen",
                                         "es": "Preguntar ahora a la IA por los casos dudosos",
                                         "it": "Chiedi ora all'IA dei casi incerti"},
    "Clear AI cache": {"nl": "AI-geheugen wissen", "fr": "Vider le cache IA", "de": "KI-Zwischenspeicher leeren",
                       "es": "Vaciar la caché de IA", "it": "Svuota la cache IA"},
    "No AI requests made in this session.": {"nl": "In deze sessie zijn geen AI-vragen gesteld.",
                                             "fr": "Aucune requête IA pendant cette session.",
                                             "de": "In dieser Sitzung gab es keine KI-Anfragen.",
                                             "es": "No se han hecho consultas de IA en esta sesión.",
                                             "it": "Nessuna richiesta IA in questa sessione."},
    "Before using AI": {"nl": "Voordat je AI gebruikt", "fr": "Avant d'utiliser l'IA", "de": "Bevor Sie KI nutzen",
                        "es": "Antes de usar la IA", "it": "Prima di usare l'IA"},
    "Some document content will be sent to the AI provider using your API key.\n\nOnly a few words around each "
    "uncertain citation or OCR word are sent - never the whole PDF - and e-mail addresses, links and long numbers "
    "in them are masked. Everything that is sent is listed in the privacy log in the AI tab. Your AI provider may "
    "charge you for this usage, and its own privacy terms apply. Choose 'Local-only' at any time to keep all "
    "content on this device.": {
        "nl": "Een deel van de documentinhoud wordt met jouw API-sleutel naar de AI-aanbieder gestuurd.\n\n"
              "Alleen enkele woorden rond elke twijfelachtige verwijzing of elk OCR-woord worden verstuurd - nooit "
              "de hele pdf - en e-mailadressen, links en lange getallen daarin worden gemaskeerd. Alles wat "
              "verstuurd wordt, staat in het privacylogboek in het AI-tabblad. Je AI-aanbieder kan hiervoor kosten "
              "aanrekenen en zijn eigen privacyvoorwaarden gelden. Kies op elk moment 'Alleen lokaal' om alles op "
              "dit apparaat te houden.",
        "fr": "Une partie du contenu du document sera envoyée au fournisseur d'IA avec votre clé API.\n\n"
              "Seuls quelques mots autour de chaque citation ou mot OCR incertain sont envoyés - jamais le PDF "
              "entier - et les adresses e-mail, liens et longs nombres y sont masqués. Tout ce qui est envoyé "
              "figure dans le journal de confidentialité de l'onglet IA. Votre fournisseur d'IA peut facturer cet "
              "usage et ses propres règles de confidentialité s'appliquent. Choisissez « Local uniquement » à tout "
              "moment pour tout garder sur cet appareil.",
        "de": "Ein Teil des Dokumentinhalts wird mit Ihrem API-Schlüssel an den KI-Anbieter gesendet.\n\n"
              "Nur einige Wörter um jedes unsichere Zitat oder OCR-Wort werden gesendet - nie das ganze PDF - und "
              "E-Mail-Adressen, Links und lange Zahlen darin werden maskiert. Alles Gesendete steht im "
              "Datenschutzprotokoll im KI-Tab. Ihr KI-Anbieter kann dafür Kosten berechnen, und es gelten seine "
              "Datenschutzbedingungen. Wählen Sie jederzeit „Nur lokal“, um alles auf diesem Gerät zu behalten.",
        "es": "Parte del contenido del documento se enviará al proveedor de IA con tu clave API.\n\n"
              "Solo se envían unas pocas palabras alrededor de cada cita o palabra OCR dudosa - nunca el PDF entero "
              "- y se ocultan los correos electrónicos, enlaces y números largos. Todo lo enviado aparece en el "
              "registro de privacidad de la pestaña IA. Tu proveedor de IA puede cobrar por este uso y se aplican "
              "sus propias condiciones de privacidad. Elige «Solo local» en cualquier momento para mantener todo "
              "en este dispositivo.",
        "it": "Parte del contenuto del documento sarà inviata al fornitore di IA con la tua chiave API.\n\n"
              "Vengono inviate solo poche parole attorno a ogni citazione o parola OCR incerta - mai l'intero PDF - "
              "e indirizzi e-mail, link e numeri lunghi vengono mascherati. Tutto ciò che viene inviato è nel "
              "registro privacy della scheda IA. Il fornitore di IA può addebitare questo uso e valgono le sue "
              "condizioni sulla privacy. Scegli «Solo locale» in qualsiasi momento per tenere tutto su questo "
              "dispositivo."},
    "I understand, enable AI": {"nl": "Begrepen, AI inschakelen", "fr": "J'ai compris, activer l'IA",
                                "de": "Verstanden, KI einschalten", "es": "Entendido, activar la IA",
                                "it": "Ho capito, attiva l'IA"},
    "Stay local-only": {"nl": "Alleen lokaal blijven", "fr": "Rester en local", "de": "Nur lokal bleiben",
                        "es": "Seguir solo en local", "it": "Resta solo locale"},
    "Enter a key first.": {"nl": "Vul eerst een sleutel in.", "fr": "Saisissez d'abord une clé.",
                           "de": "Geben Sie zuerst einen Schlüssel ein.", "es": "Introduce primero una clave.",
                           "it": "Inserisci prima una chiave."},
    "API key saved on this device.": {"nl": "API-sleutel bewaard op dit apparaat.",
                                      "fr": "Clé API enregistrée sur cet appareil.",
                                      "de": "API-Schlüssel auf diesem Gerät gespeichert.",
                                      "es": "Clave API guardada en este dispositivo.",
                                      "it": "Chiave API salvata su questo dispositivo."},
    "API key removed.": {"nl": "API-sleutel verwijderd.", "fr": "Clé API supprimée.",
                         "de": "API-Schlüssel entfernt.", "es": "Clave API eliminada.", "it": "Chiave API rimossa."},
    "AI cache cleared.": {"nl": "AI-geheugen gewist.", "fr": "Cache IA vidé.", "de": "KI-Zwischenspeicher geleert.",
                          "es": "Caché de IA vaciada.", "it": "Cache IA svuotata."},
    "Open a PDF first.": {"nl": "Open eerst een pdf.", "fr": "Ouvrez d'abord un PDF.",
                          "de": "Öffnen Sie zuerst ein PDF.", "es": "Abre primero un PDF.",
                          "it": "Apri prima un PDF."},
    "AI is off. Choose 'AI-assisted' above to use it.": {
        "nl": "AI staat uit. Kies hierboven 'Met AI-hulp' om het te gebruiken.",
        "fr": "L'IA est désactivée. Choisissez « Assisté par IA » ci-dessus pour l'utiliser.",
        "de": "KI ist aus. Wählen Sie oben „KI-gestützt“, um sie zu nutzen.",
        "es": "La IA está desactivada. Elige «Con ayuda de IA» arriba para usarla.",
        "it": "L'IA è disattivata. Scegli «Con assistenza IA» qui sopra per usarla."},
    "Sending uncertain snippets to the AI provider...": {
        "nl": "Twijfelachtige stukjes worden naar de AI-aanbieder gestuurd...",
        "fr": "Envoi des extraits incertains au fournisseur d'IA...",
        "de": "Unsichere Ausschnitte werden an den KI-Anbieter gesendet...",
        "es": "Enviando los fragmentos dudosos al proveedor de IA...",
        "it": "Invio degli estratti incerti al fornitore di IA..."},
    "The local result was kept.": {"nl": "Het lokale resultaat is behouden.", "fr": "Le résultat local a été "
                                   "conservé.", "de": "Das lokale Ergebnis wurde beibehalten.",
                                   "es": "Se ha mantenido el resultado local.",
                                   "it": "Il risultato locale è stato mantenuto."},
    "The AI request failed; the local result was kept.": {
        "nl": "De AI-vraag is mislukt; het lokale resultaat is behouden.",
        "fr": "La requête IA a échoué ; le résultat local a été conservé.",
        "de": "Die KI-Anfrage ist fehlgeschlagen; das lokale Ergebnis wurde beibehalten.",
        "es": "La consulta de IA falló; se ha mantenido el resultado local.",
        "it": "La richiesta IA non è riuscita; il risultato locale è stato mantenuto."},
    "Paid API (billed by Anthropic per token). Smaller models cost less.": {
        "nl": "Betaalde API (Anthropic rekent per token). Kleinere modellen kosten minder.",
        "fr": "API payante (facturée par Anthropic au token). Les petits modèles coûtent moins cher.",
        "de": "Kostenpflichtige API (Anthropic rechnet pro Token ab). Kleinere Modelle kosten weniger.",
        "es": "API de pago (Anthropic cobra por token). Los modelos más pequeños cuestan menos.",
        "it": "API a pagamento (Anthropic addebita per token). I modelli più piccoli costano meno."},
    "Has a free tier with rate limits (check Google's current terms). Free-tier data may be used by Google.": {
        "nl": "Heeft een gratis versie met limieten (bekijk de actuele voorwaarden van Google). Gegevens uit de "
              "gratis versie kan Google gebruiken.",
        "fr": "Offre gratuite avec limites (consultez les conditions actuelles de Google). Google peut utiliser "
              "les données de l'offre gratuite.",
        "de": "Hat eine kostenlose Stufe mit Limits (aktuelle Bedingungen von Google prüfen). Google darf Daten "
              "der kostenlosen Stufe nutzen.",
        "es": "Tiene un plan gratuito con límites (consulta las condiciones actuales de Google). Google puede usar "
              "los datos del plan gratuito.",
        "it": "Ha un piano gratuito con limiti (verifica le condizioni attuali di Google). Google può usare i dati "
              "del piano gratuito."},
    "Free 'Experiment' plan available at console.mistral.ai (rate-limited; check Mistral's current terms - "
    "free-plan data may be used to improve their models).": {
        "nl": "Gratis 'Experiment'-abonnement via console.mistral.ai (met limieten; bekijk de actuele voorwaarden "
              "van Mistral - gegevens uit het gratis abonnement kunnen gebruikt worden om hun modellen te "
              "verbeteren).",
        "fr": "Offre gratuite « Experiment » sur console.mistral.ai (avec limites ; consultez les conditions "
              "actuelles de Mistral - les données de l'offre gratuite peuvent servir à améliorer leurs modèles).",
        "de": "Kostenloser „Experiment“-Tarif auf console.mistral.ai (mit Limits; aktuelle Bedingungen von Mistral "
              "prüfen - Daten des Gratistarifs können zur Verbesserung ihrer Modelle genutzt werden).",
        "es": "Plan gratuito «Experiment» en console.mistral.ai (con límites; consulta las condiciones actuales de "
              "Mistral: los datos del plan gratuito pueden usarse para mejorar sus modelos).",
        "it": "Piano gratuito «Experiment» su console.mistral.ai (con limiti; verifica le condizioni attuali di "
              "Mistral - i dati del piano gratuito possono essere usati per migliorare i loro modelli)."},
    "No API key entered. Add one in AI Settings.": {
        "nl": "Geen API-sleutel ingevuld. Voeg er een toe bij AI-instellingen.",
        "fr": "Aucune clé API saisie. Ajoutez-en une dans Paramètres IA.",
        "de": "Kein API-Schlüssel eingegeben. Fügen Sie einen unter KI-Einstellungen hinzu.",
        "es": "No se ha introducido ninguna clave API. Añade una en Ajustes de IA.",
        "it": "Nessuna chiave API inserita. Aggiungine una in Impostazioni IA."},
    "AI is switched off (Local-only mode).": {
        "nl": "AI staat uit (modus Alleen lokaal).", "fr": "L'IA est désactivée (mode Local uniquement).",
        "de": "KI ist ausgeschaltet (Modus Nur lokal).", "es": "La IA está desactivada (modo Solo local).",
        "it": "L'IA è disattivata (modalità Solo locale)."},
    "Nothing needed AI help.": {"nl": "Niets had AI-hulp nodig.", "fr": "Rien n'avait besoin de l'IA.",
                                "de": "Nichts brauchte KI-Hilfe.", "es": "Nada necesitó ayuda de la IA.",
                                "it": "Niente aveva bisogno dell'IA."},

    # ---------------------------------------------------------------- settings tab
    "Appearance": {"nl": "Weergave", "fr": "Apparence", "de": "Darstellung", "es": "Apariencia", "it": "Aspetto"},
    "App language": {"nl": "Taal van de app", "fr": "Langue de l'appli", "de": "App-Sprache",
                     "es": "Idioma de la app", "it": "Lingua dell'app"},
    "Dark mode": {"nl": "Donkere modus", "fr": "Mode sombre", "de": "Dunkelmodus", "es": "Modo oscuro",
                  "it": "Modalità scura"},
    "High-contrast colours": {"nl": "Kleuren met hoog contrast", "fr": "Couleurs à contraste élevé",
                              "de": "Farben mit hohem Kontrast", "es": "Colores de alto contraste",
                              "it": "Colori ad alto contrasto"},
    "App text size": {"nl": "Tekstgrootte van de app", "fr": "Taille du texte de l'appli",
                      "de": "Textgröße der App", "es": "Tamaño del texto de la app",
                      "it": "Dimensione del testo dell'app"},
    "Normal": {"nl": "Normaal", "fr": "Normale", "de": "Normal", "es": "Normal", "it": "Normale"},
    "Large": {"nl": "Groot", "fr": "Grande", "de": "Groß", "es": "Grande", "it": "Grande"},
    "Larger": {"nl": "Groter", "fr": "Plus grande", "de": "Größer", "es": "Más grande", "it": "Più grande"},
    "Largest": {"nl": "Grootst", "fr": "Très grande", "de": "Am größten", "es": "Muy grande",
                "it": "Molto grande"},
    "These only change the app. Your exported documents keep their own layout and colours (see the Convert tab).": {
        "nl": "Dit verandert alleen de app. Je geëxporteerde documenten houden hun eigen opmaak en kleuren (zie "
              "het tabblad Omzetten).",
        "fr": "Ces réglages ne changent que l'appli. Vos documents exportés gardent leur propre mise en page et "
              "leurs couleurs (voir l'onglet Convertir).",
        "de": "Das ändert nur die App. Ihre exportierten Dokumente behalten ihr eigenes Layout und ihre Farben "
              "(siehe Reiter Umwandeln).",
        "es": "Esto solo cambia la app. Tus documentos exportados mantienen su propio diseño y colores (ver la "
              "pestaña Convertir).",
        "it": "Queste opzioni cambiano solo l'app. I documenti esportati mantengono impaginazione e colori propri "
              "(vedi la scheda Converti)."},
    "Text recognition (OCR)": {"nl": "Tekstherkenning (OCR)", "fr": "Reconnaissance de texte (OCR)",
                               "de": "Texterkennung (OCR)", "es": "Reconocimiento de texto (OCR)",
                               "it": "Riconoscimento del testo (OCR)"},
    "Tesseract: {path}": {"nl": "Tesseract: {path}", "fr": "Tesseract : {path}", "de": "Tesseract: {path}",
                          "es": "Tesseract: {path}", "it": "Tesseract: {path}"},
    "Tesseract was not found. Scanned pages fall back to the text the scanner stored. Get it at "
    "https://github.com/UB-Mannheim/tesseract/wiki": {
        "nl": "Tesseract is niet gevonden. Voor gescande pagina's wordt de tekst gebruikt die de scanner opsloeg. "
              "Download het via https://github.com/UB-Mannheim/tesseract/wiki",
        "fr": "Tesseract est introuvable. Les pages numérisées utilisent le texte enregistré par le scanner. "
              "Téléchargez-le sur https://github.com/UB-Mannheim/tesseract/wiki",
        "de": "Tesseract wurde nicht gefunden. Für gescannte Seiten wird der vom Scanner gespeicherte Text "
              "verwendet. Download: https://github.com/UB-Mannheim/tesseract/wiki",
        "es": "No se encontró Tesseract. Las páginas escaneadas usan el texto que guardó el escáner. Descárgalo en "
              "https://github.com/UB-Mannheim/tesseract/wiki",
        "it": "Tesseract non trovato. Per le pagine scansionate si usa il testo salvato dallo scanner. Scaricalo "
              "da https://github.com/UB-Mannheim/tesseract/wiki"},
    "Scanned documents are only read once: the result is saved on this device, so opening the same PDF again is "
    "almost instant.": {
        "nl": "Gescande documenten worden maar één keer gelezen: het resultaat wordt op dit apparaat bewaard, dus "
              "dezelfde pdf opnieuw openen gaat bijna meteen.",
        "fr": "Les documents numérisés ne sont lus qu'une fois : le résultat est gardé sur cet appareil, donc "
              "rouvrir le même PDF est presque instantané.",
        "de": "Gescannte Dokumente werden nur einmal gelesen: Das Ergebnis wird auf diesem Gerät gespeichert, "
              "daher öffnet sich dasselbe PDF danach fast sofort.",
        "es": "Los documentos escaneados solo se leen una vez: el resultado se guarda en este dispositivo, así que "
              "volver a abrir el mismo PDF es casi instantáneo.",
        "it": "I documenti scansionati vengono letti una sola volta: il risultato è salvato su questo "
              "dispositivo, quindi riaprire lo stesso PDF è quasi immediato."},
    "Clear saved OCR results": {"nl": "Bewaarde OCR-resultaten wissen", "fr": "Effacer les résultats OCR "
                                "enregistrés", "de": "Gespeicherte OCR-Ergebnisse löschen",
                                "es": "Borrar los resultados OCR guardados", "it": "Cancella i risultati OCR salvati"},
    "Saved OCR results cleared ({n} document(s)).": {
        "nl": "Bewaarde OCR-resultaten gewist ({n} document(en)).",
        "fr": "Résultats OCR enregistrés effacés ({n} document(s)).",
        "de": "Gespeicherte OCR-Ergebnisse gelöscht ({n} Dokument(e)).",
        "es": "Resultados OCR guardados borrados ({n} documento(s)).",
        "it": "Risultati OCR salvati cancellati ({n} documento/i)."},
    "Privacy and storage": {"nl": "Privacy en opslag", "fr": "Confidentialité et stockage",
                            "de": "Datenschutz und Speicher", "es": "Privacidad y almacenamiento",
                            "it": "Privacy e archiviazione"},
    "Everything is processed on this device unless you switch on AI (see AI settings). Your settings, dictionary "
    "and saved OCR results are stored here:": {
        "nl": "Alles wordt op dit apparaat verwerkt, tenzij je AI inschakelt (zie AI-instellingen). Je "
              "instellingen, woordenboek en bewaarde OCR-resultaten staan hier:",
        "fr": "Tout est traité sur cet appareil, sauf si vous activez l'IA (voir Paramètres IA). Vos réglages, "
              "votre dictionnaire et les résultats OCR enregistrés se trouvent ici :",
        "de": "Alles wird auf diesem Gerät verarbeitet, außer Sie schalten KI ein (siehe KI-Einstellungen). Ihre "
              "Einstellungen, Ihr Wörterbuch und gespeicherte OCR-Ergebnisse liegen hier:",
        "es": "Todo se procesa en este dispositivo salvo que actives la IA (ver Ajustes de IA). Tus ajustes, "
              "diccionario y resultados OCR guardados están aquí:",
        "it": "Tutto viene elaborato su questo dispositivo, a meno che non attivi l'IA (vedi Impostazioni IA). Le "
              "tue impostazioni, il dizionario e i risultati OCR salvati si trovano qui:"},
    "Support": {"nl": "Steun", "fr": "Soutien", "de": "Unterstützung", "es": "Apoyo", "it": "Sostegno"},
    "The app is free. If it helps you, you can buy the maker a coffee. This is completely optional and changes "
    "nothing in the app.": {
        "nl": "De app is gratis. Heb je er iets aan, dan kun je de maker op een koffie trakteren. Dat is helemaal "
              "vrijblijvend en verandert niets aan de app.",
        "fr": "L'appli est gratuite. Si elle vous aide, vous pouvez offrir un café à son auteur. C'est entièrement "
              "facultatif et ne change rien à l'appli.",
        "de": "Die App ist kostenlos. Wenn sie Ihnen hilft, können Sie dem Entwickler einen Kaffee spendieren. "
              "Das ist völlig freiwillig und ändert nichts an der App.",
        "es": "La app es gratuita. Si te ayuda, puedes invitar a un café a su creador. Es totalmente opcional y no "
              "cambia nada en la app.",
        "it": "L'app è gratuita. Se ti è utile, puoi offrire un caffè a chi l'ha creata. È del tutto facoltativo "
              "e non cambia nulla nell'app."},

    # ---------------------------------------------------------------- help tab
    "How it works": {"nl": "Hoe het werkt", "fr": "Comment ça marche", "de": "So funktioniert es",
                     "es": "Cómo funciona", "it": "Come funziona"},
    "1. Open a PDF. Text is extracted locally; scanned pages are read with OCR.\n2. Headings, lists, tables, "
    "figures, footnotes and references are detected with simple rules - no AI needed.\n3. Adjust the settings; "
    "the preview updates.\n4. Export to PDF, printable PDF, Word, text or Markdown.": {
        "nl": "1. Open een pdf. De tekst wordt lokaal uitgelezen; gescande pagina's worden met OCR gelezen.\n"
              "2. Koppen, lijsten, tabellen, figuren, voetnoten en bronnen worden met eenvoudige regels herkend - "
              "zonder AI.\n3. Pas de instellingen aan; het voorbeeld past zich aan.\n4. Exporteer naar pdf, pdf "
              "om af te drukken, Word, tekst of Markdown.",
        "fr": "1. Ouvrez un PDF. Le texte est extrait localement ; les pages numérisées sont lues par OCR.\n"
              "2. Titres, listes, tableaux, figures, notes et références sont détectés par des règles simples - "
              "sans IA.\n3. Ajustez les réglages ; l'aperçu se met à jour.\n4. Exportez en PDF, PDF à imprimer, "
              "Word, texte ou Markdown.",
        "de": "1. Öffnen Sie ein PDF. Der Text wird lokal ausgelesen; gescannte Seiten werden per OCR gelesen.\n"
              "2. Überschriften, Listen, Tabellen, Abbildungen, Fußnoten und Quellen werden mit einfachen Regeln "
              "erkannt - ohne KI.\n3. Passen Sie die Einstellungen an; die Vorschau aktualisiert sich.\n"
              "4. Exportieren Sie als PDF, Druck-PDF, Word, Text oder Markdown.",
        "es": "1. Abre un PDF. El texto se extrae en local; las páginas escaneadas se leen con OCR.\n2. Títulos, "
              "listas, tablas, figuras, notas y referencias se detectan con reglas sencillas, sin IA.\n3. Ajusta "
              "las opciones; la vista previa se actualiza.\n4. Exporta a PDF, PDF para imprimir, Word, texto o "
              "Markdown.",
        "it": "1. Apri un PDF. Il testo viene estratto in locale; le pagine scansionate sono lette con l'OCR.\n"
              "2. Titoli, elenchi, tabelle, figure, note e bibliografia vengono rilevati con regole semplici - "
              "senza IA.\n3. Regola le impostazioni; l'anteprima si aggiorna.\n4. Esporta in PDF, PDF da stampare, "
              "Word, testo o Markdown."},
    "What never changes": {"nl": "Wat nooit verandert", "fr": "Ce qui ne change jamais", "de": "Was sich nie ändert",
                           "es": "Lo que nunca cambia", "it": "Cosa non cambia mai"},
    "The author's words. The converter does not summarise, paraphrase, simplify or remove text. Your original PDF "
    "is never modified or overwritten.": {
        "nl": "De woorden van de auteur. De converter vat niet samen, herformuleert niet, vereenvoudigt niet en "
              "laat geen tekst weg. Je originele pdf wordt nooit gewijzigd of overschreven.",
        "fr": "Les mots de l'auteur. Le convertisseur ne résume pas, ne reformule pas, ne simplifie pas et ne "
              "supprime aucun texte. Votre PDF d'origine n'est jamais modifié ni écrasé.",
        "de": "Die Worte des Autors. Der Konverter fasst nicht zusammen, formuliert nicht um, vereinfacht nicht "
              "und entfernt keinen Text. Ihr Original-PDF wird nie verändert oder überschrieben.",
        "es": "Las palabras del autor. El conversor no resume, no parafrasea, no simplifica ni elimina texto. Tu "
              "PDF original nunca se modifica ni se sobrescribe.",
        "it": "Le parole dell'autore. Il convertitore non riassume, non riformula, non semplifica e non elimina "
              "testo. Il PDF originale non viene mai modificato né sovrascritto."},
    "The language of each PDF is detected automatically from its text. If the guess is wrong, choose the language "
    "at the top of the Convert tab.": {
        "nl": "De taal van elke pdf wordt automatisch herkend aan de tekst. Klopt de gok niet, kies dan de taal "
              "bovenaan het tabblad Omzetten.",
        "fr": "La langue de chaque PDF est détectée automatiquement à partir de son texte. Si elle est fausse, "
              "choisissez la langue en haut de l'onglet Convertir.",
        "de": "Die Sprache jedes PDFs wird automatisch am Text erkannt. Falls sie falsch ist, wählen Sie die "
              "Sprache oben im Reiter Umwandeln.",
        "es": "El idioma de cada PDF se detecta automáticamente a partir de su texto. Si no acierta, elige el "
              "idioma en la parte superior de la pestaña Convertir.",
        "it": "La lingua di ogni PDF viene rilevata automaticamente dal testo. Se è sbagliata, scegli la lingua in "
              "cima alla scheda Converti."},
    "About the presets and fonts": {"nl": "Over de voorinstellingen en lettertypes",
                                    "fr": "À propos des préréglages et des polices",
                                    "de": "Über die Vorlagen und Schriftarten",
                                    "es": "Sobre los ajustes predefinidos y las fuentes",
                                    "it": "Sulle preimpostazioni e i caratteri"},
    "No single font is best for every reader with dyslexia.": {
        "nl": "Geen enkel lettertype is het beste voor iedere lezer met dyslexie.",
        "fr": "Aucune police n'est la meilleure pour tous les lecteurs dyslexiques.",
        "de": "Keine Schriftart ist für alle Leser mit Legasthenie die beste.",
        "es": "Ninguna fuente es la mejor para todos los lectores con dislexia.",
        "it": "Nessun carattere è il migliore per ogni lettore con dislessia."},
    "App language, dark mode and text size are in the Settings tab.": {
        "nl": "De taal van de app, donkere modus en tekstgrootte vind je in het tabblad Instellingen.",
        "fr": "La langue de l'appli, le mode sombre et la taille du texte se trouvent dans l'onglet Paramètres.",
        "de": "App-Sprache, Dunkelmodus und Textgröße finden Sie im Reiter Einstellungen.",
        "es": "El idioma de la app, el modo oscuro y el tamaño del texto están en la pestaña Ajustes.",
        "it": "Lingua dell'app, modalità scura e dimensione del testo sono nella scheda Impostazioni."},

    # ---------------------------------------------------------------- loading, export, messages
    "Choose a PDF": {"nl": "Kies een pdf", "fr": "Choisissez un PDF", "de": "PDF auswählen", "es": "Elige un PDF",
                     "it": "Scegli un PDF"},
    "Reading {name}...": {"nl": "{name} wordt gelezen...", "fr": "Lecture de {name}...", "de": "{name} wird "
                          "gelesen...", "es": "Leyendo {name}...", "it": "Lettura di {name}..."},
    "Could not read {name}.": {"nl": "{name} kon niet gelezen worden.", "fr": "Impossible de lire {name}.",
                               "de": "{name} konnte nicht gelesen werden.", "es": "No se pudo leer {name}.",
                               "it": "Impossibile leggere {name}."},
    "Could not read this PDF:": {"nl": "Deze pdf kon niet gelezen worden:", "fr": "Impossible de lire ce PDF :",
                                 "de": "Dieses PDF konnte nicht gelesen werden:", "es": "No se pudo leer este PDF:",
                                 "it": "Impossibile leggere questo PDF:"},
    "{name}: {kind}. Language: {language}.": {"nl": "{name}: {kind}. Taal: {language}.",
                                              "fr": "{name} : {kind}. Langue : {language}.",
                                              "de": "{name}: {kind}. Sprache: {language}.",
                                              "es": "{name}: {kind}. Idioma: {language}.",
                                              "it": "{name}: {kind}. Lingua: {language}."},
    "selectable text": {"nl": "selecteerbare tekst", "fr": "texte sélectionnable", "de": "markierbarer Text",
                        "es": "texto seleccionable", "it": "testo selezionabile"},
    "scanned pages (the scanner's stored text was used)": {
        "nl": "gescande pagina's (de tekst van de scanner is gebruikt)",
        "fr": "pages numérisées (le texte du scanner a été utilisé)",
        "de": "gescannte Seiten (der Text des Scanners wurde verwendet)",
        "es": "páginas escaneadas (se usó el texto del escáner)",
        "it": "pagine scansionate (è stato usato il testo dello scanner)"},
    "scanned pages (text read with OCR)": {"nl": "gescande pagina's (tekst gelezen met OCR)",
                                           "fr": "pages numérisées (texte lu par OCR)",
                                           "de": "gescannte Seiten (Text per OCR gelesen)",
                                           "es": "páginas escaneadas (texto leído con OCR)",
                                           "it": "pagine scansionate (testo letto con l'OCR)"},
    "a mix of text and scanned pages (OCR used where needed)": {
        "nl": "een mix van tekst en gescande pagina's (OCR waar nodig)",
        "fr": "un mélange de texte et de pages numérisées (OCR si nécessaire)",
        "de": "eine Mischung aus Text und gescannten Seiten (OCR wo nötig)",
        "es": "una mezcla de texto y páginas escaneadas (OCR donde hace falta)",
        "it": "un misto di testo e pagine scansionate (OCR dove serve)"},
    "Page numbers must be whole numbers.": {"nl": "Paginanummers moeten gehele getallen zijn.",
                                            "fr": "Les numéros de page doivent être des nombres entiers.",
                                            "de": "Seitenzahlen müssen ganze Zahlen sein.",
                                            "es": "Los números de página deben ser enteros.",
                                            "it": "I numeri di pagina devono essere numeri interi."},
    "Saved as 'My Settings'. They will be used next time you open the app.": {
        "nl": "Opgeslagen als 'Mijn instellingen'. Ze worden gebruikt als je de app weer opent.",
        "fr": "Enregistré dans « Mes réglages ». Ils seront utilisés à la prochaine ouverture de l'appli.",
        "de": "Als „Meine Einstellungen“ gespeichert. Sie gelten beim nächsten Start der App.",
        "es": "Guardado como «Mis ajustes». Se usarán la próxima vez que abras la app.",
        "it": "Salvate come «Le mie impostazioni». Verranno usate alla prossima apertura dell'app."},
    "Default settings restored.": {"nl": "Standaardinstellingen hersteld.", "fr": "Réglages par défaut rétablis.",
                                   "de": "Standardeinstellungen wiederhergestellt.",
                                   "es": "Ajustes predeterminados restaurados.",
                                   "it": "Impostazioni predefinite ripristinate."},
    "Could not build the preview:": {"nl": "Het voorbeeld kon niet gemaakt worden:",
                                     "fr": "Impossible de créer l'aperçu :", "de": "Die Vorschau konnte nicht "
                                     "erstellt werden:", "es": "No se pudo crear la vista previa:",
                                     "it": "Impossibile creare l'anteprima:"},
    "Preparing export...": {"nl": "Export wordt voorbereid...", "fr": "Préparation de l'export...",
                            "de": "Export wird vorbereitet...", "es": "Preparando la exportación...",
                            "it": "Preparazione dell'esportazione..."},
    "Export failed:": {"nl": "Exporteren mislukt:", "fr": "Échec de l'export :", "de": "Export fehlgeschlagen:",
                       "es": "Error al exportar:", "it": "Esportazione non riuscita:"},
    "Choose where to save the file.": {"nl": "Kies waar je het bestand wilt opslaan.",
                                       "fr": "Choisissez où enregistrer le fichier.",
                                       "de": "Wählen Sie, wo die Datei gespeichert wird.",
                                       "es": "Elige dónde guardar el archivo.", "it": "Scegli dove salvare il file."},
    "Save converted file": {"nl": "Omgezet bestand opslaan", "fr": "Enregistrer le fichier converti",
                            "de": "Umgewandelte Datei speichern", "es": "Guardar el archivo convertido",
                            "it": "Salva il file convertito"},
    "That is the original PDF - choose a different name so it is not overwritten.": {
        "nl": "Dat is de originele pdf - kies een andere naam zodat die niet overschreven wordt.",
        "fr": "C'est le PDF d'origine - choisissez un autre nom pour ne pas l'écraser.",
        "de": "Das ist das Original-PDF - wählen Sie einen anderen Namen, damit es nicht überschrieben wird.",
        "es": "Ese es el PDF original: elige otro nombre para no sobrescribirlo.",
        "it": "Questo è il PDF originale - scegli un altro nome per non sovrascriverlo."},
    "Saved {name}.": {"nl": "{name} opgeslagen.", "fr": "{name} enregistré.", "de": "{name} gespeichert.",
                      "es": "{name} guardado.", "it": "{name} salvato."},
    "file": {"nl": "bestand", "fr": "fichier", "de": "Datei", "es": "archivo", "it": "file"},
    "Using the saved text recognition of this document": {
        "nl": "De bewaarde tekstherkenning van dit document wordt gebruikt",
        "fr": "Utilisation de la reconnaissance de texte enregistrée pour ce document",
        "de": "Gespeicherte Texterkennung dieses Dokuments wird verwendet",
        "es": "Usando el reconocimiento de texto guardado de este documento",
        "it": "Uso del riconoscimento del testo salvato per questo documento"},
    "Detecting document structure": {"nl": "Structuur van het document herkennen",
                                     "fr": "Détection de la structure du document",
                                     "de": "Dokumentstruktur wird erkannt", "es": "Detectando la estructura del "
                                     "documento", "it": "Rilevamento della struttura del documento"},
    "Checking OCR text against the dictionary": {"nl": "OCR-tekst wordt met het woordenboek vergeleken",
                                                 "fr": "Vérification du texte OCR avec le dictionnaire",
                                                 "de": "OCR-Text wird mit dem Wörterbuch abgeglichen",
                                                 "es": "Comprobando el texto OCR con el diccionario",
                                                 "it": "Controllo del testo OCR con il dizionario"},
    "Done": {"nl": "Klaar", "fr": "Terminé", "de": "Fertig", "es": "Listo", "it": "Fatto"},
}

# messages from the processing core, matched in i18n.MESSAGE_PATTERNS; {0}, {1}... are the parts found
PATTERNS: dict[str, dict[str, str]] = {
    "read_scanned_eta": {
        "nl": "{0} van {1} gescande pagina('s) gelezen - nog ongeveer {2}",
        "fr": "{0} page(s) numérisée(s) lue(s) sur {1} - encore environ {2}",
        "de": "{0} von {1} gescannten Seiten gelesen - noch etwa {2}",
        "es": "{0} de {1} páginas escaneadas leídas - quedan unos {2}",
        "it": "Lette {0} di {1} pagine scansionate - circa {2} rimanenti"},
    "read_scanned": {
        "nl": "{0} van {1} gescande pagina('s) gelezen", "fr": "{0} page(s) numérisée(s) lue(s) sur {1}",
        "de": "{0} von {1} gescannten Seiten gelesen", "es": "{0} de {1} páginas escaneadas leídas",
        "it": "Lette {0} di {1} pagine scansionate"},
    "reading_page": {"nl": "Pagina {0} van {1} wordt gelezen", "fr": "Lecture de la page {0} sur {1}",
                     "de": "Seite {0} von {1} wird gelesen", "es": "Leyendo la página {0} de {1}",
                     "it": "Lettura della pagina {0} di {1}"},
    "ocr_page": {"nl": "OCR op pagina {0} van {1}", "fr": "OCR de la page {0} sur {1}",
                 "de": "OCR für Seite {0} von {1}", "es": "OCR de la página {0} de {1}",
                 "it": "OCR della pagina {0} di {1}"},
    "no_ocr": {
        "nl": "{0} gescande pagina('s) blijven een afbeelding omdat er geen OCR geïnstalleerd is. Installeer "
              "Tesseract OCR om ze naar tekst om te zetten.",
        "fr": "{0} page(s) numérisée(s) restent des images car aucun moteur OCR n'est installé. Installez "
              "Tesseract OCR pour les convertir en texte.",
        "de": "{0} gescannte Seite(n) bleiben Bilder, weil keine OCR installiert ist. Installieren Sie Tesseract "
              "OCR, um sie in Text umzuwandeln.",
        "es": "{0} página(s) escaneada(s) se quedan como imagen porque no hay OCR instalado. Instala Tesseract OCR "
              "para convertirlas en texto.",
        "it": "{0} pagina/e scansionata/e restano immagini perché non è installato un OCR. Installa Tesseract OCR "
              "per convertirle in testo."},
    "text_layer": {
        "nl": "Voor {0} gescande pagina('s) is de tekst gebruikt die de scanner in de pdf opsloeg; die kan minder "
              "goed zijn. Installeer Tesseract OCR voor het beste resultaat.",
        "fr": "{0} page(s) numérisée(s) utilisent le texte enregistré par le scanner dans le PDF, parfois de moindre "
              "qualité. Installez Tesseract OCR pour un meilleur résultat.",
        "de": "Für {0} gescannte Seite(n) wurde der vom Scanner im PDF gespeicherte Text verwendet, der schlechter "
              "sein kann. Installieren Sie Tesseract OCR für das beste Ergebnis.",
        "es": "{0} página(s) escaneada(s) usan el texto que el escáner guardó en el PDF, que puede ser de menor "
              "calidad. Instala Tesseract OCR para obtener el mejor resultado.",
        "it": "Per {0} pagina/e scansionata/e è stato usato il testo salvato dallo scanner nel PDF, che può essere "
              "di qualità inferiore. Installa Tesseract OCR per il risultato migliore."},
    "pictured": {
        "nl": "De tekst die de scanner opsloeg voor pagina('s) {0} van de pdf is onleesbaar, dus (delen van) deze "
              "pagina's worden als afbeelding getoond. Installeer Tesseract OCR om ze naar tekst om te zetten.",
        "fr": "Le texte enregistré par le scanner pour la/les page(s) {0} du PDF est illisible : ces pages (ou une "
              "partie) sont affichées en image. Installez Tesseract OCR pour les convertir en texte.",
        "de": "Der vom Scanner gespeicherte Text für Seite(n) {0} des PDFs ist unlesbar, daher werden diese Seiten "
              "(teilweise) als Bild gezeigt. Installieren Sie Tesseract OCR, um sie in Text umzuwandeln.",
        "es": "El texto que guardó el escáner para la(s) página(s) {0} del PDF es ilegible, así que (partes de) "
              "esas páginas se muestran como imagen. Instala Tesseract OCR para convertirlas en texto.",
        "it": "Il testo salvato dallo scanner per la/le pagina/e {0} del PDF è illeggibile, quindi (parti di) "
              "queste pagine sono mostrate come immagine. Installa Tesseract OCR per convertirle in testo."},
    "garbled": {
        "nl": "De tekst die de scanner opsloeg voor pagina('s) {0} van de pdf bevat fouten. Installeer Tesseract "
              "OCR voor een schoner resultaat.",
        "fr": "Le texte enregistré par le scanner pour la/les page(s) {0} du PDF contient des erreurs. Installez "
              "Tesseract OCR pour un résultat plus propre.",
        "de": "Der vom Scanner gespeicherte Text für Seite(n) {0} des PDFs enthält Fehler. Installieren Sie "
              "Tesseract OCR für ein saubereres Ergebnis.",
        "es": "El texto que guardó el escáner para la(s) página(s) {0} del PDF contiene errores. Instala Tesseract "
              "OCR para un resultado más limpio.",
        "it": "Il testo salvato dallo scanner per la/le pagina/e {0} del PDF contiene errori. Installa Tesseract "
              "OCR per un risultato più pulito."},
    "sent_to_ai": {"nl": "Naar AI gestuurd: {0}", "fr": "Envoyé à l'IA : {0}", "de": "An die KI gesendet: {0}",
                   "es": "Enviado a la IA: {0}", "it": "Inviato all'IA: {0}"},
    "n_citations": {"nl": "{0} twijfelachtige verwijzing(en)", "fr": "{0} citation(s) incertaine(s)",
                    "de": "{0} unsichere(s) Zitat(e)", "es": "{0} cita(s) dudosa(s)",
                    "it": "{0} citazione/i incerta/e"},
    "n_ocr_words": {"nl": "{0} twijfelachtig(e) OCR-woord(en)", "fr": "{0} mot(s) OCR incertain(s)",
                    "de": "{0} unsichere(s) OCR-Wort/Wörter", "es": "{0} palabra(s) OCR dudosa(s)",
                    "it": "{0} parola/e OCR incerta/e"},
    "font_substitute": {
        "nl": "{0} is niet geïnstalleerd op dit apparaat; in de plaats wordt het gelijkaardige gratis lettertype "
              "{1} gebruikt.",
        "fr": "{0} n'est pas installée sur cet appareil ; la police libre similaire {1} est utilisée à la place.",
        "de": "{0} ist auf diesem Gerät nicht installiert; stattdessen wird die ähnliche freie Schrift {1} "
              "verwendet.",
        "es": "{0} no está instalada en este dispositivo; se usa en su lugar la fuente libre similar {1}.",
        "it": "{0} non è installato su questo dispositivo; al suo posto si usa il carattere libero simile {1}."},
}
