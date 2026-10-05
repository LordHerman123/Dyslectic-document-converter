"""Translations of the app's own texts, keyed by the English wording.

Each entry: English -> {"nl", "fr", "de", "es", "it"}. Keep {placeholders} exactly as in the English.
Missing entries fall back to English. tests/test_i18n.py checks that every text in the UI is translated.
"""

T: dict[str, dict[str, str]] = {
    # ---------------------------------------------------------------- focus mode
    'Eraser': {
        'nl': 'Gum',
        'fr': 'Gomme',
        'de': 'Radierer',
        'es': 'Borrador',
        'it': 'Gomma'},
    'Focus mode': {
        'nl': 'Focusmodus',
        'fr': 'Mode concentration',
        'de': 'Fokusmodus',
        'es': 'Modo concentración',
        'it': 'Modalità concentrazione'},
    'Highlighter': {
        'nl': 'Markeerstift',
        'fr': 'Surligneur',
        'de': 'Textmarker',
        'es': 'Marcador',
        'it': 'Evidenziatore'},
    'Leave focus mode': {
        'nl': 'Focusmodus verlaten',
        'fr': 'Quitter le mode concentration',
        'de': 'Fokusmodus beenden',
        'es': 'Salir del modo concentración',
        'it': 'Esci dalla modalità concentrazione'},
    'Page {n} / {total}': {
        'nl': 'Pagina {n} / {total}',
        'fr': 'Page {n} / {total}',
        'de': 'Seite {n} / {total}',
        'es': 'Página {n} / {total}',
        'it': 'Pagina {n} / {total}'},
    'Read the converted document in the whole window': {
        'nl': 'Lees het omgezette document in het hele venster',
        'fr': 'Lire le document converti dans toute la fenêtre',
        'de': 'Das umgewandelte Dokument im ganzen Fenster lesen',
        'es': 'Leer el documento convertido en toda la ventana',
        'it': 'Leggi il documento convertito a tutta finestra'},
    'Reading settings': {
        'nl': 'Leesinstellingen',
        'fr': 'Réglages de lecture',
        'de': 'Leseeinstellungen',
        'es': 'Ajustes de lectura',
        'it': 'Impostazioni di lettura'},
    'Show or hide the read-aloud controls': {
        'nl': 'Voorleesknoppen tonen of verbergen',
        'fr': 'Afficher ou masquer les commandes de lecture',
        'de': 'Vorlese-Bedienelemente ein- oder ausblenden',
        'es': 'Mostrar u ocultar los controles de lectura',
        'it': 'Mostra o nascondi i comandi di lettura'},
    'Smaller': {
        'nl': 'Kleiner',
        'fr': 'Plus petit',
        'de': 'Kleiner',
        'es': 'Más pequeño',
        'it': 'Più piccolo'},
    'Tap to read: off - clicking on the page does not start reading': {
        'nl': 'Tik om voor te lezen: uit - klikken op de pagina start het voorlezen niet',
        'fr': 'Toucher pour lire : désactivé - cliquer sur la page ne lance pas la lecture',
        'de': 'Tippen zum Vorlesen: aus - ein Klick auf die Seite startet das Vorlesen nicht',
        'es': 'Tocar para leer: desactivado - hacer clic en la página no empieza la lectura',
        'it': 'Tocca per leggere: disattivato - un clic sulla pagina non avvia la lettura'},
    'Tap to read: on - click on the page to start reading there': {
        'nl': 'Tik om voor te lezen: aan - klik op de pagina om daar te beginnen',
        'fr': 'Toucher pour lire : activé - cliquez sur la page pour commencer la lecture à cet endroit',
        'de': 'Tippen zum Vorlesen: an - klicken Sie auf die Seite, um dort zu beginnen',
        'es': 'Tocar para leer: activado - haz clic en la página para empezar a leer allí',
        'it': 'Tocca per leggere: attivo - fai clic sulla pagina per iniziare a leggere da lì'},
    'Yellow': {
        'nl': 'Geel',
        'fr': 'Jaune',
        'de': 'Gelb',
        'es': 'Amarillo',
        'it': 'Giallo'},
    'Green': {
        'nl': 'Groen',
        'fr': 'Vert',
        'de': 'Grün',
        'es': 'Verde',
        'it': 'Verde'},
    'Blue': {
        'nl': 'Blauw',
        'fr': 'Bleu',
        'de': 'Blau',
        'es': 'Azul',
        'it': 'Blu'},
    'Pink': {
        'nl': 'Roze',
        'fr': 'Rose',
        'de': 'Rosa',
        'es': 'Rosa',
        'it': 'Rosa'},
    'No {language} voice is installed on this computer, so another voice reads the text. You can add one in Windows Settings > Time & language > Speech > Add voices, then restart the app.': {
        'nl': 'Er is geen stem voor het {language} geïnstalleerd op deze computer, dus een andere stem leest de tekst. Je kunt er een toevoegen via Windows-instellingen > Tijd en taal > Spraak > Stemmen toevoegen, en daarna de app opnieuw starten.',
        'fr': "Aucune voix en {language} n'est installée sur cet ordinateur ; une autre voix lit donc le texte. Vous pouvez en ajouter une dans Paramètres Windows > Heure et langue > Voix > Ajouter des voix, puis redémarrer l'appli.",
        'de': 'Auf diesem Computer ist keine Stimme für {language} installiert, daher liest eine andere Stimme den Text. Sie können eine hinzufügen unter Windows-Einstellungen > Zeit und Sprache > Sprachausgabe > Stimmen hinzufügen und danach die App neu starten.',
        'es': 'No hay ninguna voz en {language} instalada en este ordenador, así que otra voz lee el texto. Puedes añadir una en Configuración de Windows > Hora e idioma > Voz > Agregar voces y luego reiniciar la app.',
        'it': "Su questo computer non è installata una voce in {language}, quindi il testo viene letto da un'altra voce. Puoi aggiungerne una in Impostazioni di Windows > Data/ora e lingua > Voce > Aggiungi voci e poi riavviare l'app."},
    "Reading aloud stopped because of an error:": {
        "nl": "Het voorlezen is gestopt door een fout:", "fr": "La lecture à voix haute s'est arrêtée à cause d'une erreur :",
        "de": "Das Vorlesen wurde wegen eines Fehlers beendet:", "es": "La lectura en voz alta se detuvo por un error:",
        "it": "La lettura ad alta voce si è interrotta a causa di un errore:"},
    # ---------------------------------------------------------------- help: updates
    'Updates and source code': {
        'nl': 'Updates en broncode',
        'fr': 'Mises à jour et code source',
        'de': 'Updates und Quellcode',
        'es': 'Actualizaciones y código fuente',
        'it': 'Aggiornamenti e codice sorgente'},
    'You are using version {version}. The newest version, what changed in it, and the source code are on GitHub.': {
        'nl': 'Je gebruikt versie {version}. De nieuwste versie, wat er veranderd is en de broncode staan op GitHub.',
        'fr': 'Vous utilisez la version {version}. La version la plus récente, ce qui a changé et le code source sont sur GitHub.',
        'de': 'Sie verwenden Version {version}. Die neueste Version, die Änderungen und der Quellcode sind auf GitHub.',
        'es': 'Estás usando la versión {version}. La versión más reciente, lo que ha cambiado y el código fuente están en GitHub.',
        'it': 'Stai usando la versione {version}. La versione più recente, cosa è cambiato e il codice sorgente sono su GitHub.'},
    'Project on GitHub': {
        'nl': 'Project op GitHub',
        'fr': 'Projet sur GitHub',
        'de': 'Projekt auf GitHub',
        'es': 'Proyecto en GitHub',
        'it': 'Progetto su GitHub'},
    'Opens GitHub in your web browser': {
        'nl': 'Opent GitHub in je webbrowser',
        'fr': 'Ouvre GitHub dans votre navigateur',
        'de': 'Öffnet GitHub in Ihrem Webbrowser',
        'es': 'Abre GitHub en tu navegador',
        'it': 'Apre GitHub nel browser'},
    "EPUB (e-reader)": {"nl": "EPUB (e-reader)", "fr": "EPUB (liseuse)", "de": "EPUB (E-Reader)",
                        "es": "EPUB (lector electrónico)", "it": "EPUB (e-reader)"},
    # ---------------------------------------------------------------- read aloud
    'Read aloud': {
        'nl': 'Voorlezen',
        'fr': 'Lire à voix haute',
        'de': 'Vorlesen',
        'es': 'Leer en voz alta',
        'it': 'Leggi ad alta voce'},
    'Continue': {
        'nl': 'Verder lezen',
        'fr': 'Continuer',
        'de': 'Weiterlesen',
        'es': 'Continuar',
        'it': 'Continua'},
    'Pause': {
        'nl': 'Pauze',
        'fr': 'Pause',
        'de': 'Pause',
        'es': 'Pausa',
        'it': 'Pausa'},
    'Stop': {
        'nl': 'Stoppen',
        'fr': 'Arrêter',
        'de': 'Stopp',
        'es': 'Detener',
        'it': 'Ferma'},
    'Speed': {
        'nl': 'Snelheid',
        'fr': 'Vitesse',
        'de': 'Tempo',
        'es': 'Velocidad',
        'it': 'Velocità'},
    'Voice': {
        'nl': 'Stem',
        'fr': 'Voix',
        'de': 'Stimme',
        'es': 'Voz',
        'it': 'Voce'},
    'Turn pages along': {
        'nl': "Pagina's mee omslaan",
        'fr': 'Tourner les pages en même temps',
        'de': 'Seiten mitblättern',
        'es': 'Pasar las páginas a la vez',
        'it': 'Gira le pagine insieme'},
    'No speech voices were found on this device.': {
        'nl': 'Er zijn geen voorleesstemmen gevonden op dit apparaat.',
        'fr': "Aucune voix de lecture n'a été trouvée sur cet appareil.",
        'de': 'Auf diesem Gerät wurden keine Vorlesestimmen gefunden.',
        'es': 'No se encontraron voces de lectura en este dispositivo.',
        'it': 'Nessuna voce di lettura trovata su questo dispositivo.'},
    'There is no text to read on these pages.': {
        'nl': "Er is geen tekst om voor te lezen op deze pagina's.",
        'fr': "Il n'y a pas de texte à lire sur ces pages.",
        'de': 'Auf diesen Seiten gibt es keinen Text zum Vorlesen.',
        'es': 'No hay texto para leer en estas páginas.',
        'it': "Non c'è testo da leggere in queste pagine."},
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
    "Export": {"nl": "Exporteren", "fr": "Exporter", "de": "Exportieren", "es": "Exportar", "it": "Esporta"},
    "Save the converted document": {"nl": "Het omgezette document opslaan", "fr": "Enregistrer le document converti",
                                    "de": "Das umgewandelte Dokument speichern",
                                    "es": "Guardar el documento convertido", "it": "Salva il documento convertito"},
    "Include my highlights (PDF)": {"nl": "Met mijn markeringen (PDF)", "fr": "Avec mes surlignages (PDF)",
                                    "de": "Mit meinen Markierungen (PDF)", "es": "Con mis resaltados (PDF)",
                                    "it": "Con le mie evidenziazioni (PDF)"},
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
    "system keychain": {"nl": "sleutelhanger van het systeem", "fr": "trousseau du système",
                        "de": "Schlüsselbund des Systems", "es": "llavero del sistema",
                        "it": "portachiavi di sistema"},
    "private file on this device": {"nl": "privébestand op dit apparaat", "fr": "fichier privé sur cet appareil",
                                    "de": "private Datei auf diesem Gerät", "es": "archivo privado en este "
                                    "dispositivo", "it": "file privato su questo dispositivo"},
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
    "the preview updates.\n4. Export to PDF, printable PDF, Word, EPUB, text or Markdown.": {
        "nl": "1. Open een pdf. De tekst wordt lokaal uitgelezen; gescande pagina's worden met OCR gelezen.\n"
              "2. Koppen, lijsten, tabellen, figuren, voetnoten en bronnen worden met eenvoudige regels herkend - "
              "zonder AI.\n3. Pas de instellingen aan; het voorbeeld past zich aan.\n4. Exporteer naar pdf, pdf "
              "om af te drukken, Word, EPUB, tekst of Markdown.",
        "fr": "1. Ouvrez un PDF. Le texte est extrait localement ; les pages numérisées sont lues par OCR.\n"
              "2. Titres, listes, tableaux, figures, notes et références sont détectés par des règles simples - "
              "sans IA.\n3. Ajustez les réglages ; l'aperçu se met à jour.\n4. Exportez en PDF, PDF à imprimer, "
              "Word, EPUB, texte ou Markdown.",
        "de": "1. Öffnen Sie ein PDF. Der Text wird lokal ausgelesen; gescannte Seiten werden per OCR gelesen.\n"
              "2. Überschriften, Listen, Tabellen, Abbildungen, Fußnoten und Quellen werden mit einfachen Regeln "
              "erkannt - ohne KI.\n3. Passen Sie die Einstellungen an; die Vorschau aktualisiert sich.\n"
              "4. Exportieren Sie als PDF, Druck-PDF, Word, EPUB, Text oder Markdown.",
        "es": "1. Abre un PDF. El texto se extrae en local; las páginas escaneadas se leen con OCR.\n2. Títulos, "
              "listas, tablas, figuras, notas y referencias se detectan con reglas sencillas, sin IA.\n3. Ajusta "
              "las opciones; la vista previa se actualiza.\n4. Exporta a PDF, PDF para imprimir, Word, EPUB, texto o "
              "Markdown.",
        "it": "1. Apri un PDF. Il testo viene estratto in locale; le pagine scansionate sono lette con l'OCR.\n"
              "2. Titoli, elenchi, tabelle, figure, note e bibliografia vengono rilevati con regole semplici - "
              "senza IA.\n3. Regola le impostazioni; l'anteprima si aggiorna.\n4. Esporta in PDF, PDF da stampare, "
              "Word, EPUB, testo o Markdown."},
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
    # focus mode: view options, reading ruler, word card and notes (1.8)
    'Add note': {'nl': 'Notitie toevoegen', 'fr': 'Ajouter une note', 'de': 'Notiz hinzufügen', 'es': 'Añadir nota', 'it': 'Aggiungi nota'},
    'Close': {'nl': 'Sluiten', 'fr': 'Fermer', 'de': 'Schließen', 'es': 'Cerrar', 'it': 'Chiudi'},
    'Hide the bars (Esc brings them back)': {'nl': 'De balken verbergen (Esc haalt ze terug)', 'fr': 'Masquer les barres (Échap les fait revenir)', 'de': 'Die Leisten ausblenden (Esc holt sie zurück)', 'es': 'Ocultar las barras (Esc las muestra de nuevo)', 'it': 'Nascondi le barre (Esc le riporta)'},
    'Highlight': {'nl': 'Markeren', 'fr': 'Surligner', 'de': 'Markieren', 'es': 'Resaltar', 'it': 'Evidenzia'},
    'Look up online': {'nl': 'Online opzoeken', 'fr': 'Chercher en ligne', 'de': 'Online nachschlagen', 'es': 'Buscar en línea', 'it': 'Cerca online'},
    'Make the pages as wide as the window': {'nl': "De pagina's zo breed als het venster maken", 'fr': 'Rendre les pages aussi larges que la fenêtre', 'de': 'Die Seiten so breit wie das Fenster machen', 'es': 'Hacer las páginas tan anchas como la ventana', 'it': 'Rendi le pagine larghe quanto la finestra'},
    'Note': {'nl': 'Notitie', 'fr': 'Note', 'de': 'Notiz', 'es': 'Nota', 'it': 'Nota'},
    'Opens Wiktionary in your browser': {'nl': 'Opent WikiWoordenboek in je browser', 'fr': 'Ouvre le Wiktionnaire dans votre navigateur', 'de': 'Öffnet Wiktionary in Ihrem Browser', 'es': 'Abre Wikcionario en su navegador', 'it': 'Apre il Wikizionario nel browser'},
    'Page colour': {'nl': 'Paginakleur', 'fr': 'Couleur de page', 'de': 'Seitenfarbe', 'es': 'Color de página', 'it': 'Colore della pagina'},
    'Reading ruler (move it with the arrow keys or by tapping a line)': {'nl': 'Leesliniaal (verplaats met de pijltjestoetsen of door op een regel te tikken)', 'fr': 'Règle de lecture (déplacez-la avec les flèches ou en touchant une ligne)', 'de': 'Leselineal (mit den Pfeiltasten oder durch Tippen auf eine Zeile bewegen)', 'es': 'Regla de lectura (muévala con las flechas o tocando una línea)', 'it': 'Righello di lettura (spostalo con le frecce o toccando una riga)'},
    'Remove highlight': {'nl': 'Markering verwijderen', 'fr': 'Supprimer le surlignage', 'de': 'Markierung entfernen', 'es': 'Quitar el resaltado', 'it': 'Rimuovi evidenziazione'},
    'Save note': {'nl': 'Notitie opslaan', 'fr': 'Enregistrer la note', 'de': 'Notiz speichern', 'es': 'Guardar nota', 'it': 'Salva nota'},
    'Say the word': {'nl': 'Het woord uitspreken', 'fr': 'Prononcer le mot', 'de': 'Das Wort aussprechen', 'es': 'Pronunciar la palabra', 'it': 'Pronuncia la parola'},
    'Show the bars': {'nl': 'De balken tonen', 'fr': 'Afficher les barres', 'de': 'Die Leisten zeigen', 'es': 'Mostrar las barras', 'it': 'Mostra le barre'},
    'There is no dictionary on this device for {language} yet.': {'nl': 'Er is nog geen woordenboek voor {language} op dit apparaat.', 'fr': "Il n'y a pas encore de dictionnaire pour {language} sur cet appareil.", 'de': 'Für {language} gibt es auf diesem Gerät noch kein Wörterbuch.', 'es': 'Aún no hay diccionario de {language} en este dispositivo.', 'it': "Su questo dispositivo non c'è ancora un dizionario per {language}."},
    'This word is not in the dictionary on this device.': {'nl': 'Dit woord staat niet in het woordenboek op dit apparaat.', 'fr': "Ce mot n'est pas dans le dictionnaire de cet appareil.", 'de': 'Dieses Wort steht nicht im Wörterbuch auf diesem Gerät.', 'es': 'Esta palabra no está en el diccionario de este dispositivo.', 'it': 'Questa parola non è nel dizionario di questo dispositivo.'},
    'Turn the reading view a quarter turn': {'nl': 'De leesweergave een kwartslag draaien', 'fr': "Faire pivoter la vue de lecture d'un quart de tour", 'de': 'Die Leseansicht um eine Vierteldrehung drehen', 'es': 'Girar la vista de lectura un cuarto de vuelta', 'it': 'Ruota la vista di lettura di un quarto di giro'},
    '{source} - on this device': {'nl': '{source} - op dit apparaat', 'fr': '{source} - sur cet appareil', 'de': '{source} - auf diesem Gerät', 'es': '{source} - en este dispositivo', 'it': '{source} - su questo dispositivo'},
    'Grey': {'nl': 'Grijs', 'fr': 'Gris', 'de': 'Grau', 'es': 'Gris', 'it': 'Grigio'},
    'Dark': {'nl': 'Donker', 'fr': 'Sombre', 'de': 'Dunkel', 'es': 'Oscuro', 'it': 'Scuro'},
    'noun': {'nl': 'zelfstandig naamwoord', 'fr': 'nom', 'de': 'Substantiv', 'es': 'sustantivo', 'it': 'sostantivo'},
    'verb': {'nl': 'werkwoord', 'fr': 'verbe', 'de': 'Verb', 'es': 'verbo', 'it': 'verbo'},
    'adjective': {'nl': 'bijvoeglijk naamwoord', 'fr': 'adjectif', 'de': 'Adjektiv', 'es': 'adjetivo', 'it': 'aggettivo'},
    'adverb': {'nl': 'bijwoord', 'fr': 'adverbe', 'de': 'Adverb', 'es': 'adverbio', 'it': 'avverbio'},
    # focus mode: selecting text, notes and the notes list (1.9)
    'Edit note': {'nl': 'Notitie bewerken', 'fr': 'Modifier la note', 'de': 'Notiz bearbeiten', 'es': 'Editar nota', 'it': 'Modifica nota'},
    'End': {'nl': 'Einde', 'fr': 'Fin', 'de': 'Ende', 'es': 'Final', 'it': 'Fine'},
    'Export notes as a list': {'nl': 'Notities als lijst exporteren', 'fr': 'Exporter les notes en liste', 'de': 'Notizen als Liste exportieren', 'es': 'Exportar notas como lista', 'it': 'Esporta le note come elenco'},
    'Notes and highlights': {'nl': 'Notities en markeringen', 'fr': 'Notes et surlignages', 'de': 'Notizen und Markierungen', 'es': 'Notas y resaltados', 'it': 'Note ed evidenziazioni'},
    'Notes on {name}': {'nl': 'Notities bij {name}', 'fr': 'Notes sur {name}', 'de': 'Notizen zu {name}', 'es': 'Notas sobre {name}', 'it': 'Note su {name}'},
    'Nothing highlighted yet. Hold a word and drag to select text.': {'nl': 'Nog niets gemarkeerd. Houd een woord vast en sleep om tekst te selecteren.', 'fr': "Rien n'est encore surligné. Maintenez un mot et faites glisser pour sélectionner du texte.", 'de': 'Noch nichts markiert. Halten Sie ein Wort gedrückt und ziehen Sie, um Text auszuwählen.', 'es': 'Aún no hay nada resaltado. Mantén pulsada una palabra y arrastra para seleccionar texto.', 'it': 'Ancora nulla di evidenziato. Tieni premuta una parola e trascina per selezionare il testo.'},
    'One word earlier': {'nl': 'Eén woord eerder', 'fr': 'Un mot plus tôt', 'de': 'Ein Wort früher', 'es': 'Una palabra antes', 'it': 'Una parola prima'},
    'One word later': {'nl': 'Eén woord later', 'fr': 'Un mot plus loin', 'de': 'Ein Wort später', 'es': 'Una palabra después', 'it': 'Una parola dopo'},
    'Page {n}': {'nl': 'Pagina {n}', 'fr': 'Page {n}', 'de': 'Seite {n}', 'es': 'Página {n}', 'it': 'Pagina {n}'},
    'Paragraph': {'nl': 'Alinea', 'fr': 'Paragraphe', 'de': 'Absatz', 'es': 'Párrafo', 'it': 'Paragrafo'},
    'Save your highlights and notes as a Word document': {'nl': 'Je markeringen en notities opslaan als Word-document', 'fr': 'Enregistrer vos surlignages et notes en document Word', 'de': 'Ihre Markierungen und Notizen als Word-Dokument speichern', 'es': 'Guardar tus resaltados y notas como documento de Word', 'it': 'Salva evidenziazioni e note come documento Word'},
    'Select': {'nl': 'Selecteren', 'fr': 'Sélectionner', 'de': 'Auswählen', 'es': 'Seleccionar', 'it': 'Seleziona'},
    'Sentence': {'nl': 'Zin', 'fr': 'Phrase', 'de': 'Satz', 'es': 'Frase', 'it': 'Frase'},
    'Speak your note (Windows voice typing)': {'nl': 'Je notitie inspreken (Windows-spraakinvoer)', 'fr': 'Dicter votre note (saisie vocale Windows)', 'de': 'Notiz diktieren (Windows-Spracheingabe)', 'es': 'Dictar tu nota (escritura por voz de Windows)', 'it': 'Detta la nota (digitazione vocale di Windows)'},
    'Start': {'nl': 'Begin', 'fr': 'Début', 'de': 'Anfang', 'es': 'Inicio', 'it': 'Inizio'},
    'Tip: press the microphone to speak your note': {'nl': 'Tip: druk op de microfoon om je notitie in te spreken', 'fr': 'Astuce : appuyez sur le micro pour dicter votre note', 'de': 'Tipp: Tippen Sie auf das Mikrofon, um Ihre Notiz zu diktieren', 'es': 'Consejo: pulsa el micrófono para dictar tu nota', 'it': 'Suggerimento: premi il microfono per dettare la nota'},
    'Voice typing could not be started. Press Windows + H to start it.': {'nl': 'Spraakinvoer kon niet worden gestart. Druk op Windows + H om hem te starten.', 'fr': "La saisie vocale n'a pas pu démarrer. Appuyez sur Windows + H pour la lancer.", 'de': 'Die Spracheingabe konnte nicht gestartet werden. Drücken Sie Windows + H, um sie zu starten.', 'es': 'No se pudo iniciar la escritura por voz. Pulsa Windows + H para iniciarla.', 'it': 'Impossibile avviare la digitazione vocale. Premi Windows + H per avviarla.'},
    'With notes': {'nl': 'Met notities', 'fr': 'Avec notes', 'de': 'Mit Notizen', 'es': 'Con notas', 'it': 'Con note'},
    'Word': {'nl': 'Woord', 'fr': 'Mot', 'de': 'Wort', 'es': 'Palabra', 'it': 'Parola'},
    'Your note': {'nl': 'Je notitie', 'fr': 'Votre note', 'de': 'Ihre Notiz', 'es': 'Tu nota', 'it': 'La tua nota'},
    # focus mode: selection toolbar, copy and undo (1.10)
    '1 word': {'nl': '1 woord', 'fr': '1 mot', 'de': '1 Wort', 'es': '1 palabra', 'it': '1 parola'},
    '{n} words': {'nl': '{n} woorden', 'fr': '{n} mots', 'de': '{n} Wörter', 'es': '{n} palabras', 'it': '{n} parole'},
    'Add or edit a note (N)': {'nl': 'Notitie toevoegen of bewerken (N)', 'fr': 'Ajouter ou modifier une note (N)', 'de': 'Notiz hinzufügen oder bearbeiten (N)', 'es': 'Añadir o editar una nota (N)', 'it': 'Aggiungi o modifica una nota (N)'},
    'Close (Esc)': {'nl': 'Sluiten (Esc)', 'fr': 'Fermer (Échap)', 'de': 'Schließen (Esc)', 'es': 'Cerrar (Esc)', 'it': 'Chiudi (Esc)'},
    'Copied.': {'nl': 'Gekopieerd.', 'fr': 'Copié.', 'de': 'Kopiert.', 'es': 'Copiado.', 'it': 'Copiato.'},
    'Copy': {'nl': 'Kopiëren', 'fr': 'Copier', 'de': 'Kopieren', 'es': 'Copiar', 'it': 'Copia'},
    'Highlight removed': {'nl': 'Markering verwijderd', 'fr': 'Surlignage supprimé', 'de': 'Markierung entfernt', 'es': 'Resaltado eliminado', 'it': 'Evidenziazione rimossa'},
    'Highlighted in {colour}': {'nl': 'Gemarkeerd in {colour}', 'fr': 'Surligné en {colour}', 'de': 'In {colour} markiert', 'es': 'Resaltado en {colour}', 'it': 'Evidenziato in {colour}'},
    'Meaning': {'nl': 'Betekenis', 'fr': 'Sens', 'de': 'Bedeutung', 'es': 'Significado', 'it': 'Significato'},
    'More: select the sentence or paragraph, adjust': {'nl': 'Meer: de zin of alinea selecteren, aanpassen', 'fr': 'Plus : sélectionner la phrase ou le paragraphe, ajuster', 'de': 'Mehr: Satz oder Absatz auswählen, anpassen', 'es': 'Más: seleccionar la frase o el párrafo, ajustar', 'it': 'Altro: seleziona la frase o il paragrafo, regola'},
    'Read': {'nl': 'Voorlezen', 'fr': 'Lire', 'de': 'Vorlesen', 'es': 'Leer', 'it': 'Leggi'},
    'Remove': {'nl': 'Verwijderen', 'fr': 'Supprimer', 'de': 'Entfernen', 'es': 'Quitar', 'it': 'Rimuovi'},
    'Remove the highlight (Delete)': {'nl': 'De markering verwijderen (Delete)', 'fr': 'Supprimer le surlignage (Suppr)', 'de': 'Die Markierung entfernen (Entf)', 'es': 'Quitar el resaltado (Supr)', 'it': "Rimuovi l'evidenziazione (Canc)"},
    'Pages with an unusual layout (reading order)': {'nl': 'Pagina’s met een ongewone opmaak (leesvolgorde)', 'fr': 'Pages à la mise en page inhabituelle (ordre de lecture)', 'de': 'Seiten mit ungewöhnlichem Layout (Lesereihenfolge)', 'es': 'Páginas con un diseño poco habitual (orden de lectura)', 'it': "Pagine con un'impaginazione insolita (ordine di lettura)"},
    'Page layout': {'nl': 'Pagina-opmaak', 'fr': 'Mise en page', 'de': 'Seitenlayout', 'es': 'Diseño de página', 'it': 'Impaginazione'},
    'Page layout: the first and last words of each piece of the page': {'nl': 'Pagina-opmaak: de eerste en laatste woorden van elk stuk van de pagina', 'fr': 'Mise en page : les premiers et derniers mots de chaque partie de la page', 'de': 'Seitenlayout: die ersten und letzten Wörter jedes Teils der Seite', 'es': 'Diseño de página: las primeras y últimas palabras de cada parte de la página', 'it': 'Impaginazione: le prime e ultime parole di ogni parte della pagina'},
    'Summary': {'nl': 'Samenvatting', 'fr': 'Résumé', 'de': 'Zusammenfassung', 'es': 'Resumen', 'it': 'Riassunto'},
    'Saved as a note.': {'nl': 'Opgeslagen als notitie.', 'fr': 'Enregistré comme note.', 'de': 'Als Notiz gespeichert.', 'es': 'Guardado como nota.', 'it': 'Salvato come nota.'},
    'Summarise': {'nl': 'Samenvatten', 'fr': 'Résumer', 'de': 'Zusammenfassen', 'es': 'Resumir', 'it': 'Riassumi'},
    "AI is off. Choose 'AI-assisted' in AI settings to use it.": {'nl': "AI staat uit. Kies 'AI-ondersteund' in de AI-instellingen om het te gebruiken.", 'fr': "L'IA est désactivée. Choisissez « Assisté par IA » dans les réglages IA pour l'utiliser.", 'de': 'KI ist aus. Wählen Sie „KI-gestützt“ in den KI-Einstellungen, um sie zu nutzen.', 'es': 'La IA está desactivada. Elige «Asistido por IA» en los ajustes de IA para usarla.', 'it': "L'IA è disattivata. Scegli «Assistito da IA» nelle impostazioni IA per usarla."},
    'AI summary (check it against the text):': {'nl': 'AI-samenvatting (controleer ze met de tekst):', 'fr': 'Résumé IA (vérifiez-le avec le texte) :', 'de': 'KI-Zusammenfassung (mit dem Text abgleichen):', 'es': 'Resumen de IA (compruébalo con el texto):', 'it': 'Riassunto IA (verificalo con il testo):'},
    'AI summary': {'nl': 'AI-samenvatting', 'fr': 'Résumé IA', 'de': 'KI-Zusammenfassung', 'es': 'Resumen de IA', 'it': 'Riassunto IA'},
    'AI summary (AI is off)': {'nl': 'AI-samenvatting (AI staat uit)', 'fr': "Résumé IA (l'IA est désactivée)", 'de': 'KI-Zusammenfassung (KI ist aus)', 'es': 'Resumen de IA (la IA está desactivada)', 'it': "Riassunto IA (l'IA è disattivata)"},
    'Plain language (short sentences, easy words)': {'nl': 'Eenvoudige taal (korte zinnen, makkelijke woorden)', 'fr': 'Langage simple (phrases courtes, mots faciles)', 'de': 'Einfache Sprache (kurze Sätze, leichte Wörter)', 'es': 'Lenguaje sencillo (frases cortas, palabras fáciles)', 'it': 'Linguaggio semplice (frasi brevi, parole facili)'},
    'Summarising...': {'nl': 'Bezig met samenvatten...', 'fr': 'Résumé en cours...', 'de': 'Wird zusammengefasst...', 'es': 'Resumiendo...', 'it': 'Riassunto in corso...'},
    'To get a summary of a page, section or selection, switch on AI-assisted mode in AI settings. Nothing is sent to an AI provider until you do.': {'nl': 'Zet AI-ondersteunde modus aan in de AI-instellingen om een samenvatting van een pagina, sectie of selectie te krijgen. Er wordt niets naar een AI-aanbieder gestuurd tot je dat doet.', 'fr': "Pour obtenir le résumé d'une page, d'une section ou d'une sélection, activez le mode assisté par IA dans les réglages IA. Rien n'est envoyé à un fournisseur d'IA avant cela.", 'de': 'Um eine Zusammenfassung einer Seite, eines Abschnitts oder einer Auswahl zu erhalten, schalten Sie in den KI-Einstellungen den KI-gestützten Modus ein. Bis dahin wird nichts an einen KI-Anbieter gesendet.', 'es': 'Para obtener un resumen de una página, sección o selección, activa el modo asistido por IA en los ajustes de IA. No se envía nada a un proveedor de IA hasta que lo hagas.', 'it': 'Per ottenere il riassunto di una pagina, sezione o selezione, attiva la modalità assistita da IA nelle impostazioni IA. Nulla viene inviato a un fornitore di IA finché non lo fai.'},
    'Length': {'nl': 'Lengte', 'fr': 'Longueur', 'de': 'Länge', 'es': 'Longitud', 'it': 'Lunghezza'},
    'The summary could not be made:': {'nl': 'De samenvatting kon niet gemaakt worden:', 'fr': "Le résumé n'a pas pu être créé :", 'de': 'Die Zusammenfassung konnte nicht erstellt werden:', 'es': 'No se pudo hacer el resumen:', 'it': 'Non è stato possibile creare il riassunto:'},
    'AI summary of the selection': {'nl': 'AI-samenvatting van de selectie', 'fr': 'Résumé IA de la sélection', 'de': 'KI-Zusammenfassung der Auswahl', 'es': 'Resumen de IA de la selección', 'it': 'Riassunto IA della selezione'},
    'Not now': {'nl': 'Niet nu', 'fr': 'Pas maintenant', 'de': 'Nicht jetzt', 'es': 'Ahora no', 'it': 'Non ora'},
    'Open AI settings': {'nl': 'AI-instellingen openen', 'fr': 'Ouvrir les réglages IA', 'de': 'KI-Einstellungen öffnen', 'es': 'Abrir ajustes de IA', 'it': 'Apri impostazioni IA'},
    'About {n} words will be sent to {provider} ({model}). Every request is recorded in the privacy log.': {'nl': 'Ongeveer {n} woorden worden naar {provider} ({model}) gestuurd. Elk verzoek wordt in het privacylogboek bijgehouden.', 'fr': 'Environ {n} mots seront envoyés à {provider} ({model}). Chaque requête est inscrite dans le journal de confidentialité.', 'de': 'Etwa {n} Wörter werden an {provider} ({model}) gesendet. Jede Anfrage wird im Datenschutzprotokoll festgehalten.', 'es': 'Se enviarán unas {n} palabras a {provider} ({model}). Cada solicitud queda registrada en el registro de privacidad.', 'it': 'Circa {n} parole saranno inviate a {provider} ({model}). Ogni richiesta viene registrata nel registro della privacy.'},
    'Save as note': {'nl': 'Opslaan als notitie', 'fr': 'Enregistrer comme note', 'de': 'Als Notiz speichern', 'es': 'Guardar como nota', 'it': 'Salva come nota'},
    'AI summaries are off': {'nl': 'AI-samenvattingen staan uit', 'fr': 'Les résumés IA sont désactivés', 'de': 'KI-Zusammenfassungen sind aus', 'es': 'Los resúmenes de IA están desactivados', 'it': 'I riassunti IA sono disattivati'},
    'Made by AI': {'nl': 'Gemaakt door AI', 'fr': 'Créé par IA', 'de': 'Von KI erstellt', 'es': 'Hecho por IA', 'it': "Creato dall'IA"},
    'AI can make mistakes. Check the summary against the text before you use it.': {'nl': 'AI kan fouten maken. Controleer de samenvatting met de tekst voor je ze gebruikt.', 'fr': "L'IA peut se tromper. Vérifiez le résumé avec le texte avant de l'utiliser.", 'de': 'KI kann Fehler machen. Gleichen Sie die Zusammenfassung mit dem Text ab, bevor Sie sie verwenden.', 'es': 'La IA puede equivocarse. Comprueba el resumen con el texto antes de usarlo.', 'it': "L'IA può sbagliare. Verifica il riassunto con il testo prima di usarlo."},
    'Short': {'nl': 'Kort', 'fr': 'Court', 'de': 'Kurz', 'es': 'Corto', 'it': 'Breve'},
    'Detailed': {'nl': 'Uitgebreid', 'fr': 'Détaillé', 'de': 'Ausführlich', 'es': 'Detallado', 'it': 'Dettagliato'},
    "With AI-assisted mode on, Focus mode can make a summary on request. It is shown next to the text, marked as made by AI, and never replaces the author's words.": {'nl': 'Met AI-ondersteunde modus aan kan de focusmodus op verzoek een samenvatting maken. Die staat naast de tekst, is gemarkeerd als gemaakt door AI en vervangt nooit de woorden van de auteur.', 'fr': "Avec le mode assisté par IA, le mode focus peut faire un résumé sur demande. Il s'affiche à côté du texte, marqué comme créé par IA, et ne remplace jamais les mots de l'auteur.", 'de': 'Mit KI-gestütztem Modus kann der Fokusmodus auf Wunsch eine Zusammenfassung erstellen. Sie steht neben dem Text, ist als von KI erstellt markiert und ersetzt nie die Worte des Autors.', 'es': 'Con el modo asistido por IA, el modo enfoque puede hacer un resumen a petición. Se muestra junto al texto, marcado como hecho por IA, y nunca sustituye las palabras del autor.', 'it': "Con la modalità assistita da IA, la modalità focus può creare un riassunto su richiesta. Viene mostrato accanto al testo, segnato come creato dall'IA, e non sostituisce mai le parole dell'autore."},
    'Model ({provider})': {'nl': 'Model ({provider})', 'fr': 'Modèle ({provider})', 'de': 'Modell ({provider})', 'es': 'Modelo ({provider})', 'it': 'Modello ({provider})'},
    '{provider} · from the {var} environment variable': {'nl': '{provider} · uit de omgevingsvariabele {var}', 'fr': "{provider} · depuis la variable d'environnement {var}", 'de': '{provider} · aus der Umgebungsvariable {var}', 'es': '{provider} · de la variable de entorno {var}', 'it': "{provider} · dalla variabile d'ambiente {var}"},
    'Name': {'nl': 'Naam', 'fr': 'Nom', 'de': 'Name', 'es': 'Nombre', 'it': 'Nome'},
    'e.g. Uni key': {'nl': 'bv. Sleutel unief', 'fr': 'ex. Clé fac', 'de': 'z. B. Uni-Schlüssel', 'es': 'p. ej. Clave uni', 'it': 'es. Chiave uni'},
    '{provider} · key ending in …{end}': {'nl': '{provider} · sleutel eindigend op …{end}', 'fr': '{provider} · clé se terminant par …{end}', 'de': '{provider} · Schlüssel endet auf …{end}', 'es': '{provider} · clave que termina en …{end}', 'it': '{provider} · chiave che termina con …{end}'},
    'Test': {'nl': 'Testen', 'fr': 'Tester', 'de': 'Testen', 'es': 'Probar', 'it': 'Prova'},
    'Testing...': {'nl': 'Bezig met testen...', 'fr': 'Test en cours...', 'de': 'Wird getestet...', 'es': 'Probando...', 'it': 'Prova in corso...'},
    'Connection check': {'nl': 'Verbindingstest', 'fr': 'Test de connexion', 'de': 'Verbindungstest', 'es': 'Prueba de conexión', 'it': 'Prova di connessione'},
    'No keys yet. Add one below.': {'nl': 'Nog geen sleutels. Voeg er hieronder een toe.', 'fr': 'Aucune clé pour le moment. Ajoutez-en une ci-dessous.', 'de': 'Noch keine Schlüssel. Fügen Sie unten einen hinzu.', 'es': 'Aún no hay claves. Añade una abajo.', 'it': 'Ancora nessuna chiave. Aggiungine una qui sotto.'},
    'Not tested yet': {'nl': 'Nog niet getest', 'fr': 'Pas encore testée', 'de': 'Noch nicht getestet', 'es': 'Aún no probada', 'it': 'Non ancora provata'},
    'Remove this key?': {'nl': 'Deze sleutel verwijderen?', 'fr': 'Supprimer cette clé ?', 'de': 'Diesen Schlüssel entfernen?', 'es': '¿Quitar esta clave?', 'it': 'Rimuovere questa chiave?'},
    "'{name}' is deleted from this device. You can add it again later.": {'nl': "'{name}' wordt van dit apparaat verwijderd. Je kunt hem later opnieuw toevoegen.", 'fr': "« {name} » sera supprimée de cet appareil. Vous pourrez l'ajouter à nouveau plus tard.", 'de': '„{name}“ wird von diesem Gerät gelöscht. Sie können ihn später wieder hinzufügen.', 'es': '«{name}» se eliminará de este dispositivo. Puedes volver a añadirla más tarde.', 'it': '«{name}» verrà eliminata da questo dispositivo. Potrai aggiungerla di nuovo più tardi.'},
    'API keys': {'nl': 'API-sleutels', 'fr': 'Clés API', 'de': 'API-Schlüssel', 'es': 'Claves API', 'it': 'Chiavi API'},
    "Keys are kept on this device ({where}), never in settings or logs. The key marked 'In use' is the one AI requests use; click another to switch.": {'nl': "Sleutels blijven op dit apparaat ({where}), nooit in de instellingen of logboeken. De sleutel met 'In gebruik' wordt voor AI-verzoeken gebruikt; klik op een andere om te wisselen.", 'fr': 'Les clés restent sur cet appareil ({where}), jamais dans les réglages ni les journaux. La clé marquée « Utilisée » sert aux requêtes IA ; cliquez sur une autre pour changer.', 'de': 'Schlüssel bleiben auf diesem Gerät ({where}), nie in Einstellungen oder Protokollen. Der Schlüssel mit „In Gebrauch“ wird für KI-Anfragen verwendet; klicken Sie auf einen anderen, um zu wechseln.', 'es': 'Las claves se guardan en este dispositivo ({where}), nunca en los ajustes ni en los registros. La clave marcada «En uso» es la que usan las solicitudes de IA; haz clic en otra para cambiar.', 'it': "Le chiavi restano su questo dispositivo ({where}), mai nelle impostazioni o nei registri. La chiave segnata «In uso» è quella usata per le richieste IA; fai clic su un'altra per cambiare."},
    'Add a key': {'nl': 'Een sleutel toevoegen', 'fr': 'Ajouter une clé', 'de': 'Einen Schlüssel hinzufügen', 'es': 'Añadir una clave', 'it': 'Aggiungi una chiave'},
    'Test sends one tiny request with the word "test" - never document text - and checks that the key and model work. Tests are shown in the privacy log too.': {'nl': 'Testen stuurt één heel klein verzoek met het woord "test" - nooit tekst uit het document - en controleert of de sleutel en het model werken. Tests staan ook in het privacylogboek.', 'fr': 'Le test envoie une toute petite requête avec le mot « test » - jamais le texte du document - et vérifie que la clé et le modèle fonctionnent. Les tests figurent aussi dans le journal de confidentialité.', 'de': 'Der Test sendet eine winzige Anfrage mit dem Wort „test“ - nie Text aus dem Dokument - und prüft, ob Schlüssel und Modell funktionieren. Tests stehen auch im Datenschutzprotokoll.', 'es': 'La prueba envía una solicitud mínima con la palabra «test» - nunca texto del documento - y comprueba que la clave y el modelo funcionan. Las pruebas también aparecen en el registro de privacidad.', 'it': 'La prova invia una richiesta minima con la parola «test» - mai testo del documento - e verifica che la chiave e il modello funzionino. Le prove compaiono anche nel registro della privacy.'},
    'In use': {'nl': 'In gebruik', 'fr': 'Utilisée', 'de': 'In Gebrauch', 'es': 'En uso', 'it': 'In uso'},
    'Remove this key': {'nl': 'Deze sleutel verwijderen', 'fr': 'Supprimer cette clé', 'de': 'Diesen Schlüssel entfernen', 'es': 'Quitar esta clave', 'it': 'Rimuovi questa chiave'},
    'Works: the key is valid and the AI answered.': {'nl': 'Werkt: de sleutel is geldig en de AI antwoordde.', 'fr': "Ça marche : la clé est valide et l'IA a répondu.", 'de': 'Funktioniert: Der Schlüssel ist gültig und die KI hat geantwortet.', 'es': 'Funciona: la clave es válida y la IA respondió.', 'it': "Funziona: la chiave è valida e l'IA ha risposto."},
    'Connected · answered in {s} s · tested at {time}': {'nl': 'Verbonden · antwoord in {s} s · getest om {time}', 'fr': 'Connectée · réponse en {s} s · testée à {time}', 'de': 'Verbunden · Antwort in {s} s · getestet um {time}', 'es': 'Conectada · respondió en {s} s · probada a las {time}', 'it': 'Connessa · risposta in {s} s · provata alle {time}'},
    'Use this key': {'nl': 'Deze sleutel gebruiken', 'fr': 'Utiliser cette clé', 'de': 'Diesen Schlüssel verwenden', 'es': 'Usar esta clave', 'it': 'Usa questa chiave'},
    'Test connection': {'nl': 'Verbinding testen', 'fr': 'Tester la connexion', 'de': 'Verbindung testen', 'es': 'Probar la conexión', 'it': 'Prova la connessione'},
    'Add key': {'nl': 'Sleutel toevoegen', 'fr': 'Ajouter la clé', 'de': 'Schlüssel hinzufügen', 'es': 'Añadir clave', 'it': 'Aggiungi chiave'},
    'Open a PDF.': {'nl': 'Open een pdf.', 'fr': 'Ouvrez un PDF.', 'de': 'Öffnen Sie ein PDF.', 'es': 'Abre un PDF.', 'it': 'Apri un PDF.'},
    'Choose a preset and adjust it; the preview updates.': {'nl': 'Kies een voorinstelling en pas ze aan; het voorbeeld past zich aan.', 'fr': "Choisissez un préréglage et ajustez-le ; l'aperçu se met à jour.", 'de': 'Wählen Sie eine Vorlage und passen Sie sie an; die Vorschau wird aktualisiert.', 'es': 'Elige un ajuste predefinido y ajústalo; la vista previa se actualiza.', 'it': "Scegli una preimpostazione e regolala; l'anteprima si aggiorna."},
    'Read it in Focus mode, or have it read aloud.': {'nl': 'Lees het in de focusmodus, of laat het voorlezen.', 'fr': 'Lisez-le en mode concentration, ou faites-le lire à voix haute.', 'de': 'Lesen Sie es im Fokusmodus oder lassen Sie es vorlesen.', 'es': 'Léelo en el modo concentración o haz que te lo lean en voz alta.', 'it': 'Leggilo in modalità concentrazione o fattelo leggere ad alta voce.'},
    'Export it to the format you need.': {'nl': 'Exporteer het naar het formaat dat je nodig hebt.', 'fr': 'Exportez-le dans le format dont vous avez besoin.', 'de': 'Exportieren Sie es in das Format, das Sie brauchen.', 'es': 'Expórtalo al formato que necesites.', 'it': 'Esportalo nel formato che ti serve.'},
    'Convert a PDF': {'nl': 'Een pdf omzetten', 'fr': 'Convertir un PDF', 'de': 'Ein PDF umwandeln', 'es': 'Convertir un PDF', 'it': 'Convertire un PDF'},
    'Presets, fonts, spacing, structure and page layout': {'nl': 'Voorinstellingen, lettertypes, witruimte, structuur en pagina-opmaak', 'fr': 'Préréglages, polices, espacement, structure et mise en page', 'de': 'Vorlagen, Schriften, Abstände, Struktur und Seitenlayout', 'es': 'Ajustes predefinidos, fuentes, espaciado, estructura y diseño de página', 'it': 'Preimpostazioni, caratteri, spaziatura, struttura e impaginazione'},
    'The Convert tab turns a PDF into a calmer layout: a clear font, more space between lines, words and letters, and a clean page without clutter. The words themselves stay exactly the same.': {'nl': 'Het tabblad Omzetten maakt van een pdf een rustigere opmaak: een duidelijk lettertype, meer ruimte tussen regels, woorden en letters, en een opgeruimde pagina. De woorden zelf blijven precies hetzelfde.', 'fr': "L'onglet Convertir donne au PDF une mise en page plus calme : une police claire, plus d'espace entre les lignes, les mots et les lettres, et une page épurée. Les mots eux-mêmes restent exactement les mêmes.", 'de': 'Der Reiter Umwandeln macht aus einem PDF ein ruhigeres Layout: eine klare Schrift, mehr Abstand zwischen Zeilen, Wörtern und Buchstaben und eine aufgeräumte Seite. Die Wörter selbst bleiben genau gleich.', 'es': 'La pestaña Convertir da al PDF un diseño más tranquilo: una fuente clara, más espacio entre líneas, palabras y letras, y una página despejada. Las palabras siguen siendo exactamente las mismas.', 'it': "La scheda Converti dà al PDF un'impaginazione più calma: un carattere chiaro, più spazio tra righe, parole e lettere, e una pagina ordinata. Le parole restano esattamente le stesse."},
    'PDF, printable PDF, Word, EPUB, text or Markdown': {'nl': 'PDF, pdf om af te drukken, Word, EPUB, tekst of Markdown', 'fr': 'PDF, PDF à imprimer, Word, EPUB, texte ou Markdown', 'de': 'PDF, Druck-PDF, Word, EPUB, Text oder Markdown', 'es': 'PDF, PDF para imprimir, Word, EPUB, texto o Markdown', 'it': 'PDF, PDF da stampare, Word, EPUB, testo o Markdown'},
    'Save the converted document in the way that suits how you read: on a screen, on paper, or on an e-reader. You can also keep editing it in Word.': {'nl': 'Bewaar het omgezette document zoals het best past bij hoe je leest: op een scherm, op papier of op een e-reader. Je kunt het ook verder bewerken in Word.', 'fr': 'Enregistrez le document converti selon votre façon de lire : sur écran, sur papier ou sur une liseuse. Vous pouvez aussi continuer à le modifier dans Word.', 'de': 'Speichern Sie das umgewandelte Dokument so, wie Sie lesen: am Bildschirm, auf Papier oder auf einem E-Reader. Sie können es auch in Word weiter bearbeiten.', 'es': 'Guarda el documento convertido de la forma que mejor encaje con cómo lees: en pantalla, en papel o en un lector electrónico. También puedes seguir editándolo en Word.', 'it': 'Salva il documento convertito nel modo più adatto a come leggi: sullo schermo, su carta o su un e-reader. Puoi anche continuare a modificarlo in Word.'},
    'Scanned documents': {'nl': 'Gescande documenten', 'fr': 'Documents numérisés', 'de': 'Gescannte Dokumente', 'es': 'Documentos escaneados', 'it': 'Documenti scansionati'},
    'Text recognition and checking uncertain words': {'nl': 'Tekstherkenning en twijfelachtige woorden nakijken', 'fr': 'Reconnaissance de texte et vérification des mots incertains', 'de': 'Texterkennung und Prüfen unsicherer Wörter', 'es': 'Reconocimiento de texto y revisión de palabras dudosas', 'it': 'Riconoscimento del testo e controllo delle parole incerte'},
    'Scanned pages are pictures of text. The app reads them with text recognition (OCR) on this device, so they can be converted like any other PDF. It shows you the words it was not sure about.': {'nl': "Gescande pagina's zijn afbeeldingen van tekst. De app leest ze met tekstherkenning (OCR) op dit apparaat, zodat ze net als elke andere pdf omgezet kunnen worden. Ze toont je de woorden waarover ze twijfelde.", 'fr': "Les pages numérisées sont des images de texte. L'application les lit avec la reconnaissance de texte (OCR) sur cet appareil, pour les convertir comme n'importe quel PDF. Elle vous montre les mots dont elle n'était pas sûre.", 'de': 'Gescannte Seiten sind Bilder von Text. Die App liest sie mit Texterkennung (OCR) auf diesem Gerät, damit sie wie jedes andere PDF umgewandelt werden können. Sie zeigt Ihnen die Wörter, bei denen sie unsicher war.', 'es': 'Las páginas escaneadas son imágenes de texto. La aplicación las lee con reconocimiento de texto (OCR) en este dispositivo, para convertirlas como cualquier otro PDF. Te muestra las palabras de las que no estaba segura.', 'it': "Le pagine scansionate sono immagini di testo. L'app le legge con il riconoscimento del testo (OCR) su questo dispositivo, così si possono convertire come qualsiasi altro PDF. Ti mostra le parole su cui non era sicura."},
    'Jump to any heading': {'nl': 'Spring naar elke kop', 'fr': "Aller à n'importe quel titre", 'de': 'Zu jeder Überschrift springen', 'es': 'Salta a cualquier título', 'it': 'Vai a qualsiasi titolo'},
    'Long documents are easier to follow when you can see how they are built. The map lists the headings, so you always know where you are.': {'nl': 'Lange documenten zijn makkelijker te volgen als je ziet hoe ze opgebouwd zijn. Het overzicht toont de koppen, zodat je altijd weet waar je bent.', 'fr': 'Les longs documents sont plus faciles à suivre quand on voit leur structure. Le plan liste les titres, pour que vous sachiez toujours où vous êtes.', 'de': 'Lange Dokumente sind leichter zu verfolgen, wenn man ihren Aufbau sieht. Die Übersicht listet die Überschriften, damit Sie immer wissen, wo Sie sind.', 'es': 'Los documentos largos son más fáciles de seguir cuando ves cómo están construidos. El mapa enumera los títulos, para que siempre sepas dónde estás.', 'it': 'I documenti lunghi sono più facili da seguire quando ne vedi la struttura. La mappa elenca i titoli, così sai sempre dove ti trovi.'},
    'Hear the text, with each word highlighted': {'nl': 'Hoor de tekst, met elk woord gemarkeerd', 'fr': 'Écoutez le texte, chaque mot mis en évidence', 'de': 'Hören Sie den Text, jedes Wort hervorgehoben', 'es': 'Escucha el texto, con cada palabra resaltada', 'it': 'Ascolta il testo, con ogni parola evidenziata'},
    'Listening while you read makes long texts easier to take in. The app uses the voices installed on your computer, so the text is never sent online.': {'nl': 'Luisteren terwijl je leest maakt lange teksten makkelijker. De app gebruikt de stemmen die op je computer staan, dus de tekst gaat nooit online.', 'fr': "Écouter pendant la lecture rend les longs textes plus faciles. L'application utilise les voix installées sur votre ordinateur : le texte n'est jamais envoyé en ligne.", 'de': 'Zuhören beim Lesen macht lange Texte leichter. Die App nutzt die Stimmen, die auf Ihrem Computer installiert sind, der Text wird also nie ins Internet gesendet.', 'es': 'Escuchar mientras lees hace que los textos largos sean más fáciles. La aplicación usa las voces instaladas en tu ordenador, así que el texto nunca se envía a internet.', 'it': "Ascoltare mentre leggi rende più facili i testi lunghi. L'app usa le voci installate sul tuo computer, quindi il testo non viene mai inviato online."},
    'A calm reading view of the converted pages': {'nl': "Een rustige leesweergave van de omgezette pagina's", 'fr': 'Une vue de lecture calme des pages converties', 'de': 'Eine ruhige Leseansicht der umgewandelten Seiten', 'es': 'Una vista de lectura tranquila de las páginas convertidas', 'it': 'Una vista di lettura tranquilla delle pagine convertite'},
    'Focus mode shows only the converted pages, in the whole window, without the settings around them. It is made for reading, and you can set it up the way that is most comfortable for you.': {'nl': "De focusmodus toont alleen de omgezette pagina's, in het hele venster, zonder de instellingen eromheen. Hij is gemaakt om te lezen, en je stelt hem in zoals het voor jou het prettigst is.", 'fr': "Le mode concentration n'affiche que les pages converties, dans toute la fenêtre, sans les réglages autour. Il est fait pour lire, et vous le réglez comme cela vous convient le mieux.", 'de': 'Der Fokusmodus zeigt nur die umgewandelten Seiten im ganzen Fenster, ohne die Einstellungen drumherum. Er ist zum Lesen gemacht, und Sie richten ihn so ein, wie es für Sie am angenehmsten ist.', 'es': 'El modo concentración muestra solo las páginas convertidas, en toda la ventana, sin los ajustes alrededor. Está hecho para leer, y lo configuras como te resulte más cómodo.', 'it': 'La modalità concentrazione mostra solo le pagine convertite, in tutta la finestra, senza le impostazioni intorno. È fatta per leggere, e la imposti come ti è più comodo.'},
    'Select, highlight and take notes': {'nl': 'Selecteren, markeren en notities maken', 'fr': 'Sélectionner, surligner et prendre des notes', 'de': 'Auswählen, markieren und Notizen machen', 'es': 'Seleccionar, resaltar y tomar notas', 'it': 'Selezionare, evidenziare e prendere appunti'},
    'In Focus mode': {'nl': 'In de focusmodus', 'fr': 'En mode concentration', 'de': 'Im Fokusmodus', 'es': 'En el modo concentración', 'it': 'In modalità concentrazione'},
    'Mark what matters while you read, and write down your thoughts next to it. Highlights and notes are saved for each document and can be exported.': {'nl': 'Markeer wat belangrijk is terwijl je leest, en schrijf je gedachten erbij. Markeringen en notities worden per document bewaard en kunnen geëxporteerd worden.', 'fr': 'Surlignez ce qui compte pendant la lecture et notez vos idées à côté. Les surlignages et les notes sont enregistrés pour chaque document et peuvent être exportés.', 'de': 'Markieren Sie beim Lesen, was wichtig ist, und schreiben Sie Ihre Gedanken dazu. Markierungen und Notizen werden je Dokument gespeichert und können exportiert werden.', 'es': 'Resalta lo importante mientras lees y anota tus ideas al lado. Los resaltados y las notas se guardan para cada documento y se pueden exportar.', 'it': 'Evidenzia ciò che conta mentre leggi e annota i tuoi pensieri accanto. Evidenziazioni e note vengono salvate per ogni documento e si possono esportare.'},
    'AI (optional)': {'nl': 'AI (optioneel)', 'fr': 'IA (facultative)', 'de': 'KI (optional)', 'es': 'IA (opcional)', 'it': 'IA (facoltativa)'},
    'Off unless you switch it on': {'nl': 'Uit, tenzij je ze aanzet', 'fr': "Désactivée sauf si vous l'activez", 'de': 'Aus, außer Sie schalten sie ein', 'es': 'Desactivada salvo que la actives', 'it': 'Disattivata finché non la attivi'},
    'The app never needs AI. If you want, AI can help with the few things the app is unsure about, and make summaries. It uses your own API key, and you always see what is sent.': {'nl': 'De app heeft nooit AI nodig. Als je wilt, kan AI helpen bij de paar dingen waarover de app twijfelt, en samenvattingen maken. Ze gebruikt je eigen API-sleutel, en je ziet altijd wat er verstuurd wordt.', 'fr': "L'application n'a jamais besoin de l'IA. Si vous le souhaitez, l'IA peut aider pour les quelques points incertains et faire des résumés. Elle utilise votre propre clé API, et vous voyez toujours ce qui est envoyé.", 'de': 'Die App braucht nie KI. Wenn Sie möchten, hilft KI bei den wenigen Dingen, bei denen die App unsicher ist, und erstellt Zusammenfassungen. Sie nutzt Ihren eigenen API-Schlüssel, und Sie sehen immer, was gesendet wird.', 'es': 'La aplicación nunca necesita IA. Si quieres, la IA puede ayudar con las pocas cosas de las que la aplicación no está segura y hacer resúmenes. Usa tu propia clave API y siempre ves lo que se envía.', 'it': "L'app non ha mai bisogno dell'IA. Se vuoi, l'IA può aiutare con le poche cose di cui l'app non è sicura e creare riassunti. Usa la tua chiave API e vedi sempre cosa viene inviato."},
    'How the app itself looks': {'nl': 'Hoe de app zelf eruitziet', 'fr': "L'apparence de l'application elle-même", 'de': 'Wie die App selbst aussieht', 'es': 'Cómo se ve la propia aplicación', 'it': "Come appare l'app stessa"},
    'Change how the app itself looks, so it is comfortable for your eyes.': {'nl': 'Verander hoe de app zelf eruitziet, zodat ze prettig is voor je ogen.', 'fr': "Changez l'apparence de l'application pour qu'elle soit agréable pour vos yeux.", 'de': 'Ändern Sie, wie die App selbst aussieht, damit sie angenehm für Ihre Augen ist.', 'es': 'Cambia cómo se ve la propia aplicación para que sea cómoda para tus ojos.', 'it': "Cambia l'aspetto dell'app, così è comoda per i tuoi occhi."},
    'Copy the selection': {'nl': 'De selectie kopiëren', 'fr': 'Copier la sélection', 'de': 'Die Auswahl kopieren', 'es': 'Copiar la selección', 'it': 'Copia la selezione'},
    'Highlight the selection in a colour': {'nl': 'De selectie in een kleur markeren', 'fr': 'Surligner la sélection dans une couleur', 'de': 'Die Auswahl in einer Farbe markieren', 'es': 'Resaltar la selección en un color', 'it': 'Evidenzia la selezione con un colore'},
    'Write a note': {'nl': 'Een notitie schrijven', 'fr': 'Écrire une note', 'de': 'Eine Notiz schreiben', 'es': 'Escribir una nota', 'it': 'Scrivi una nota'},
    'Remove the highlight': {'nl': 'De markering verwijderen', 'fr': 'Supprimer le surlignage', 'de': 'Die Markierung entfernen', 'es': 'Quitar el resaltado', 'it': "Rimuovi l'evidenziazione"},
    'Stop selecting, close the toolbar, or show the bars': {'nl': 'Stoppen met selecteren, de werkbalk sluiten of de balken tonen', 'fr': "Arrêter la sélection, fermer la barre d'outils ou afficher les barres", 'de': 'Auswahl beenden, Werkzeugleiste schließen oder die Leisten zeigen', 'es': 'Dejar de seleccionar, cerrar la barra de herramientas o mostrar las barras', 'it': 'Smetti di selezionare, chiudi la barra degli strumenti o mostra le barre'},
    'Move the reading ruler, or scroll': {'nl': 'De leesliniaal verplaatsen, of scrollen', 'fr': 'Déplacer la règle de lecture, ou faire défiler', 'de': 'Das Leselineal verschieben oder scrollen', 'es': 'Mover la regla de lectura o desplazarse', 'it': 'Sposta il righello di lettura o scorri'},
    'Previous or next page': {'nl': 'Vorige of volgende pagina', 'fr': 'Page précédente ou suivante', 'de': 'Vorherige oder nächste Seite', 'es': 'Página anterior o siguiente', 'it': 'Pagina precedente o successiva'},
    'Keyboard shortcuts': {'nl': 'Sneltoetsen', 'fr': 'Raccourcis clavier', 'de': 'Tastenkürzel', 'es': 'Atajos de teclado', 'it': 'Scorciatoie da tastiera'},
    'Keys that make Focus mode quicker to use with a keyboard.': {'nl': 'Toetsen waarmee je de focusmodus sneller met een toetsenbord gebruikt.', 'fr': 'Des touches pour utiliser plus vite le mode concentration au clavier.', 'de': 'Tasten, mit denen Sie den Fokusmodus schneller mit der Tastatur nutzen.', 'es': 'Teclas para usar el modo concentración más rápido con el teclado.', 'it': 'Tasti per usare più rapidamente la modalità concentrazione con la tastiera.'},
    'Start here': {'nl': 'Begin hier', 'fr': 'Commencez ici', 'de': 'Hier beginnen', 'es': 'Empieza aquí', 'it': 'Inizia qui'},
    'Open a section below to see what else the app can do.': {'nl': 'Open hieronder een onderdeel om te zien wat de app nog meer kan.', 'fr': "Ouvrez une section ci-dessous pour voir ce que l'application sait faire d'autre.", 'de': 'Öffnen Sie unten einen Abschnitt, um zu sehen, was die App noch kann.', 'es': 'Abre una sección abajo para ver qué más puede hacer la aplicación.', 'it': "Apri una sezione qui sotto per vedere cos'altro sa fare l'app."},
    'Open PDF:': {'nl': 'PDF openen:', 'fr': 'Ouvrir un PDF :', 'de': 'PDF öffnen:', 'es': 'Abrir PDF:', 'it': 'Apri PDF:'},
    'choose a file. Its text is read on this device; scanned pages are read with OCR.': {'nl': "kies een bestand. De tekst wordt op dit apparaat gelezen; gescande pagina's met OCR.", 'fr': 'choisissez un fichier. Son texte est lu sur cet appareil ; les pages numérisées sont lues par OCR.', 'de': 'wählen Sie eine Datei. Ihr Text wird auf diesem Gerät gelesen; gescannte Seiten mit OCR.', 'es': 'elige un archivo. Su texto se lee en este dispositivo; las páginas escaneadas, con OCR.', 'it': "scegli un file. Il testo viene letto su questo dispositivo; le pagine scansionate con l'OCR."},
    'Preset:': {'nl': 'Voorinstelling:', 'fr': 'Préréglage :', 'de': 'Vorlage:', 'es': 'Ajuste predefinido:', 'it': 'Preimpostazione:'},
    "start from a preset, then change the font, size, spacing, margins and page colour. Keep your choice with 'Save as My Settings'.": {'nl': "begin bij een voorinstelling en verander dan lettertype, grootte, witruimte, marges en paginakleur. Bewaar je keuze met 'Opslaan als Mijn instellingen'.", 'fr': "partez d'un préréglage, puis changez la police, la taille, l'espacement, les marges et la couleur de page. Gardez votre choix avec « Enregistrer dans Mes réglages ».", 'de': 'beginnen Sie mit einer Vorlage und ändern Sie dann Schrift, Größe, Abstände, Ränder und Seitenfarbe. Behalten Sie Ihre Wahl mit „Als Meine Einstellungen speichern“.', 'es': 'parte de un ajuste predefinido y cambia la fuente, el tamaño, el espaciado, los márgenes y el color de página. Guarda tu elección con «Guardar como Mis ajustes».', 'it': 'parti da una preimpostazione, poi cambia carattere, dimensione, spaziatura, margini e colore della pagina. Conserva la scelta con «Salva come Le mie impostazioni».'},
    'Bold start of words:': {'nl': 'Vet begin van woorden:', 'fr': 'Début des mots en gras :', 'de': 'Wortanfänge fett:', 'es': 'Inicio de palabras en negrita:', 'it': 'Inizio delle parole in grassetto:'},
    'bolds the first part of each word. It only changes how words look.': {'nl': 'zet het eerste deel van elk woord vet. Het verandert alleen hoe woorden eruitzien.', 'fr': "met en gras le début de chaque mot. Cela ne change que l'apparence des mots.", 'de': 'macht den ersten Teil jedes Wortes fett. Es ändert nur, wie Wörter aussehen.', 'es': 'pone en negrita la primera parte de cada palabra. Solo cambia cómo se ven las palabras.', 'it': "mette in grassetto la prima parte di ogni parola. Cambia solo l'aspetto delle parole."},
    'Structure:': {'nl': 'Structuur:', 'fr': 'Structure :', 'de': 'Struktur:', 'es': 'Estructura:', 'it': 'Struttura:'},
    'hide running headers and page numbers, move footnotes to the end, turn author-year citations into numbers, and rebuild tables.': {'nl': 'verberg kopteksten en paginanummers, zet voetnoten achteraan, maak van auteur-jaar-verwijzingen nummers, en bouw tabellen opnieuw op.', 'fr': 'masquez les en-têtes et numéros de page, placez les notes de bas de page à la fin, transformez les citations auteur-année en numéros et reconstruisez les tableaux.', 'de': 'blenden Sie Kopfzeilen und Seitenzahlen aus, verschieben Sie Fußnoten ans Ende, machen Sie aus Autor-Jahr-Zitaten Nummern und bauen Sie Tabellen neu auf.', 'es': 'oculta encabezados y números de página, lleva las notas al pie al final, convierte las citas autor-año en números y reconstruye las tablas.', 'it': 'nascondi intestazioni e numeri di pagina, sposta le note a piè di pagina alla fine, trasforma le citazioni autore-anno in numeri e ricostruisci le tabelle.'},
    'Pages to convert:': {'nl': "Pagina's om om te zetten:", 'fr': 'Pages à convertir :', 'de': 'Umzuwandelnde Seiten:', 'es': 'Páginas que convertir:', 'it': 'Pagine da convertire:'},
    'convert only part of a long PDF.': {'nl': 'zet maar een deel van een lange pdf om.', 'fr': "ne convertissez qu'une partie d'un long PDF.", 'de': 'wandeln Sie nur einen Teil eines langen PDFs um.', 'es': 'convierte solo una parte de un PDF largo.', 'it': 'converti solo una parte di un PDF lungo.'},
    'Document language:': {'nl': 'Taal van het document:', 'fr': 'Langue du document :', 'de': 'Dokumentsprache:', 'es': 'Idioma del documento:', 'it': 'Lingua del documento:'},
    'found automatically. If the guess is wrong, choose the language at the top of the Convert tab.': {'nl': 'wordt automatisch gevonden. Klopt de gok niet, kies dan de taal bovenaan het tabblad Omzetten.', 'fr': "détectée automatiquement. Si ce n'est pas la bonne, choisissez la langue en haut de l'onglet Convertir.", 'de': 'wird automatisch erkannt. Stimmt sie nicht, wählen Sie die Sprache oben im Reiter Umwandeln.', 'es': 'se detecta automáticamente. Si no acierta, elige el idioma arriba en la pestaña Convertir.', 'it': 'viene rilevata automaticamente. Se non è giusta, scegli la lingua in alto nella scheda Converti.'},
    'Original, Converted, Both:': {'nl': 'Origineel, Omgezet, Beide:', 'fr': 'Original, Converti, Les deux :', 'de': 'Original, Umgewandelt, Beide:', 'es': 'Original, Convertido, Ambos:', 'it': 'Originale, Convertito, Entrambi:'},
    'compare the pages side by side; both sides stay on the same page.': {'nl': "vergelijk de pagina's naast elkaar; beide kanten blijven op dezelfde pagina.", 'fr': 'comparez les pages côte à côte ; les deux côtés restent sur la même page.', 'de': 'vergleichen Sie die Seiten nebeneinander; beide Seiten bleiben auf derselben Seite.', 'es': 'compara las páginas una al lado de la otra; ambos lados se quedan en la misma página.', 'it': 'confronta le pagine affiancate; entrambi i lati restano sulla stessa pagina.'},
    'Export button:': {'nl': 'Knop Exporteren:', 'fr': 'Bouton Exporter :', 'de': 'Schaltfläche Exportieren:', 'es': 'Botón Exportar:', 'it': 'Pulsante Esporta:'},
    'PDF for the screen, Printable PDF for A4 paper, Word (DOCX), EPUB for e-readers, plain text and Markdown.': {'nl': 'PDF voor het scherm, pdf om af te drukken op A4-papier, Word (DOCX), EPUB voor e-readers, platte tekst en Markdown.', 'fr': "PDF pour l'écran, PDF à imprimer sur papier A4, Word (DOCX), EPUB pour les liseuses, texte brut et Markdown.", 'de': 'PDF für den Bildschirm, Druck-PDF für A4-Papier, Word (DOCX), EPUB für E-Reader, reiner Text und Markdown.', 'es': 'PDF para la pantalla, PDF para imprimir en papel A4, Word (DOCX), EPUB para lectores electrónicos, texto sin formato y Markdown.', 'it': 'PDF per lo schermo, PDF da stampare su carta A4, Word (DOCX), EPUB per e-reader, testo semplice e Markdown.'},
    'Your highlights:': {'nl': 'Je markeringen:', 'fr': 'Vos surlignages :', 'de': 'Ihre Markierungen:', 'es': 'Tus resaltados:', 'it': 'Le tue evidenziazioni:'},
    "when a document has highlights, 'Include my highlights (PDF)' in the Export menu puts them in the PDF, with your notes as comments.": {'nl': "heeft een document markeringen, dan zet 'Met mijn markeringen (PDF)' in het menu Exporteren ze in de pdf, met je notities als opmerkingen.", 'fr': 'quand un document a des surlignages, « Avec mes surlignages (PDF) » dans le menu Exporter les met dans le PDF, avec vos notes en commentaires.', 'de': 'hat ein Dokument Markierungen, fügt „Mit meinen Markierungen (PDF)“ im Menü Exportieren sie ins PDF ein, mit Ihren Notizen als Kommentare.', 'es': 'cuando un documento tiene resaltados, «Con mis resaltados (PDF)» en el menú Exportar los pone en el PDF, con tus notas como comentarios.', 'it': 'quando un documento ha evidenziazioni, «Con le mie evidenziazioni (PDF)» nel menu Esporta le mette nel PDF, con le tue note come commenti.'},
    'Your original:': {'nl': 'Je origineel:', 'fr': 'Votre original :', 'de': 'Ihr Original:', 'es': 'Tu original:', 'it': 'Il tuo originale:'},
    'the PDF you opened is never changed.': {'nl': 'de pdf die je opende, wordt nooit veranderd.', 'fr': "le PDF que vous avez ouvert n'est jamais modifié.", 'de': 'das geöffnete PDF wird nie verändert.', 'es': 'el PDF que abriste nunca se cambia.', 'it': 'il PDF che hai aperto non viene mai modificato.'},
    'Clean-up:': {'nl': 'Opruimen:', 'fr': 'Nettoyage :', 'de': 'Bereinigen:', 'es': 'Limpieza:', 'it': 'Pulizia:'},
    'scans are straightened, dark borders are removed, and two-page book scans can be split into single pages.': {'nl': "scans worden rechtgezet, donkere randen verdwijnen, en scans van twee boekpagina's kunnen in losse pagina's gesplitst worden.", 'fr': 'les numérisations sont redressées, les bords sombres retirés, et les doubles pages de livre peuvent être séparées en pages simples.', 'de': 'Scans werden gerade gerichtet, dunkle Ränder entfernt, und Doppelseiten aus Büchern können in einzelne Seiten geteilt werden.', 'es': 'los escaneos se enderezan, se quitan los bordes oscuros y las dobles páginas de libro se pueden dividir en páginas sueltas.', 'it': 'le scansioni vengono raddrizzate, i bordi scuri rimossi e le doppie pagine di libro si possono dividere in pagine singole.'},
    'OCR review tab:': {'nl': 'Tabblad OCR-controle:', 'fr': 'Onglet Vérification OCR :', 'de': 'Reiter OCR-Prüfung:', 'es': 'Pestaña Revisión OCR:', 'it': 'Scheda Revisione OCR:'},
    'check the words the app was unsure about: accept, reject, or type the right text. Every change can be undone.': {'nl': 'kijk de woorden na waarover de app twijfelde: aanvaard, weiger of typ de juiste tekst. Elke wijziging kan ongedaan gemaakt worden.', 'fr': "vérifiez les mots dont l'application n'était pas sûre : acceptez, refusez ou tapez le bon texte. Chaque modification peut être annulée.", 'de': 'prüfen Sie die Wörter, bei denen die App unsicher war: annehmen, ablehnen oder den richtigen Text eintippen. Jede Änderung lässt sich rückgängig machen.', 'es': 'revisa las palabras de las que la aplicación no estaba segura: acepta, rechaza o escribe el texto correcto. Cada cambio se puede deshacer.', 'it': "controlla le parole su cui l'app non era sicura: accetta, rifiuta o scrivi il testo giusto. Ogni modifica si può annullare."},
    'My dictionary:': {'nl': 'Mijn woordenboek:', 'fr': 'Mon dictionnaire :', 'de': 'Mein Wörterbuch:', 'es': 'Mi diccionario:', 'it': 'Il mio dizionario:'},
    'add names and technical terms so they are not seen as mistakes.': {'nl': 'voeg namen en vaktermen toe, zodat ze niet als fout gezien worden.', 'fr': "ajoutez des noms et des termes techniques pour qu'ils ne soient pas vus comme des erreurs.", 'de': 'fügen Sie Namen und Fachbegriffe hinzu, damit sie nicht als Fehler gelten.', 'es': 'añade nombres y términos técnicos para que no se vean como errores.', 'it': 'aggiungi nomi e termini tecnici perché non vengano visti come errori.'},
    'Saved:': {'nl': 'Bewaard:', 'fr': 'Enregistré :', 'de': 'Gespeichert:', 'es': 'Guardado:', 'it': 'Salvato:'},
    'a scan is read only once; the result is kept on this device.': {'nl': 'een scan wordt maar één keer gelezen; het resultaat blijft op dit apparaat.', 'fr': "une numérisation n'est lue qu'une fois ; le résultat reste sur cet appareil.", 'de': 'ein Scan wird nur einmal gelesen; das Ergebnis bleibt auf diesem Gerät.', 'es': 'un escaneo se lee solo una vez; el resultado se queda en este dispositivo.', 'it': 'una scansione viene letta una sola volta; il risultato resta su questo dispositivo.'},
    'Headings:': {'nl': 'Koppen:', 'fr': 'Titres :', 'de': 'Überschriften:', 'es': 'Títulos:', 'it': 'Titoli:'},
    'every heading found in the document. Select one to show it in the preview.': {'nl': 'elke kop die in het document gevonden is. Kies er een om hem in het voorbeeld te tonen.', 'fr': "chaque titre trouvé dans le document. Choisissez-en un pour l'afficher dans l'aperçu.", 'de': 'jede im Dokument gefundene Überschrift. Wählen Sie eine, um sie in der Vorschau zu zeigen.', 'es': 'cada título encontrado en el documento. Elige uno para mostrarlo en la vista previa.', 'it': "ogni titolo trovato nel documento. Scegline uno per mostrarlo nell'anteprima."},
    'Contents page:': {'nl': 'Inhoudsopgave:', 'fr': 'Table des matières :', 'de': 'Inhaltsverzeichnis:', 'es': 'Índice:', 'it': 'Indice:'},
    "switch on 'Contents page (document map)' in the Convert tab to put one at the start of the converted document.": {'nl': "zet 'Inhoudsopgave (documentoverzicht)' aan in het tabblad Omzetten om er een vooraan het omgezette document te zetten.", 'fr': "activez « Table des matières (plan du document) » dans l'onglet Convertir pour en placer une au début du document converti.", 'de': 'schalten Sie „Inhaltsverzeichnis (Dokumentübersicht)“ im Reiter Umwandeln ein, um eines an den Anfang des umgewandelten Dokuments zu setzen.', 'es': 'activa «Índice (mapa del documento)» en la pestaña Convertir para poner uno al principio del documento convertido.', 'it': "attiva «Indice (mappa del documento)» nella scheda Converti per metterne uno all'inizio del documento convertito."},
    'Read aloud button:': {'nl': 'Knop Voorlezen:', 'fr': 'Bouton Lire à voix haute :', 'de': 'Schaltfläche Vorlesen:', 'es': 'Botón Leer en voz alta:', 'it': 'Pulsante Leggi ad alta voce:'},
    'opens the play button, voice and speed. The sentence and the word being read are highlighted.': {'nl': 'opent de afspeelknop, stem en snelheid. De zin en het woord die voorgelezen worden, zijn gemarkeerd.', 'fr': 'ouvre le bouton de lecture, la voix et la vitesse. La phrase et le mot lus sont mis en évidence.', 'de': 'öffnet Wiedergabetaste, Stimme und Tempo. Der Satz und das Wort, die gerade gelesen werden, sind hervorgehoben.', 'es': 'abre el botón de reproducir, la voz y la velocidad. La frase y la palabra que se leen aparecen resaltadas.', 'it': 'apre il pulsante di riproduzione, la voce e la velocità. La frase e la parola lette sono evidenziate.'},
    'Tap to read (hand button):': {'nl': 'Tikken om voor te lezen (handje):', 'fr': 'Toucher pour lire (bouton main) :', 'de': 'Tippen zum Vorlesen (Hand-Taste):', 'es': 'Tocar para leer (botón de la mano):', 'it': 'Tocca per leggere (pulsante mano):'},
    'off when the app starts, so clicking the text selects it. Switch it on to start reading where you click.': {'nl': 'staat uit als de app start, zodat klikken op de tekst hem selecteert. Zet het aan om te beginnen lezen waar je klikt.', 'fr': "désactivé au démarrage, pour qu'un clic sur le texte le sélectionne. Activez-le pour commencer la lecture là où vous cliquez.", 'de': 'beim Start aus, damit ein Klick auf den Text ihn auswählt. Schalten Sie es ein, um dort vorzulesen, wo Sie klicken.', 'es': 'desactivado al iniciar, para que al hacer clic en el texto se seleccione. Actívalo para empezar a leer donde hagas clic.', 'it': "disattivato all'avvio, così un clic sul testo lo seleziona. Attivalo per iniziare a leggere dove fai clic."},
    'Text size and zoom:': {'nl': 'Tekstgrootte en zoom:', 'fr': 'Taille du texte et zoom :', 'de': 'Textgröße und Zoom:', 'es': 'Tamaño del texto y zoom:', 'it': 'Dimensione del testo e zoom:'},
    'make the pages larger or smaller, fit them to the window, or pinch on a touch screen.': {'nl': "maak de pagina's groter of kleiner, pas ze aan het venster aan, of knijp op een touchscreen.", 'fr': 'agrandissez ou réduisez les pages, ajustez-les à la fenêtre, ou pincez sur un écran tactile.', 'de': 'machen Sie die Seiten größer oder kleiner, passen Sie sie ans Fenster an oder zoomen Sie mit zwei Fingern auf einem Touchscreen.', 'es': 'haz las páginas más grandes o más pequeñas, ajústalas a la ventana o pellizca en una pantalla táctil.', 'it': 'ingrandisci o riduci le pagine, adattale alla finestra o usa il pizzico su uno schermo touch.'},
    'Reading ruler:': {'nl': 'Leesliniaal:', 'fr': 'Règle de lecture :', 'de': 'Leselineal:', 'es': 'Regla de lectura:', 'it': 'Righello di lettura:'},
    'a band that marks the line you are reading; move it with the arrow keys.': {'nl': 'een band die de regel toont die je leest; verplaats hem met de pijltjestoetsen.', 'fr': 'une bande qui marque la ligne que vous lisez ; déplacez-la avec les flèches.', 'de': 'ein Band, das die Zeile markiert, die Sie lesen; verschieben Sie es mit den Pfeiltasten.', 'es': 'una banda que marca la línea que lees; muévela con las flechas.', 'it': 'una banda che segna la riga che stai leggendo; spostala con i tasti freccia.'},
    'Hide the bars:': {'nl': 'De balken verbergen:', 'fr': 'Masquer les barres :', 'de': 'Die Leisten ausblenden:', 'es': 'Ocultar las barras:', 'it': 'Nascondi le barre:'},
    'shows only the page. Press Esc to bring the bars back.': {'nl': 'toont alleen de pagina. Druk op Esc om de balken terug te halen.', 'fr': "n'affiche que la page. Appuyez sur Échap pour faire revenir les barres.", 'de': 'zeigt nur die Seite. Drücken Sie Esc, um die Leisten zurückzuholen.', 'es': 'muestra solo la página. Pulsa Esc para que vuelvan las barras.', 'it': 'mostra solo la pagina. Premi Esc per far tornare le barre.'},
    'Select:': {'nl': 'Selecteren:', 'fr': 'Sélectionner :', 'de': 'Auswählen:', 'es': 'Seleccionar:', 'it': 'Selezionare:'},
    'drag over the text with a mouse or pen. With a finger, press and hold, then drag. Double-click selects one word.': {'nl': 'sleep over de tekst met een muis of pen. Met een vinger: houd ingedrukt en sleep dan. Dubbelklikken selecteert één woord.', 'fr': 'faites glisser sur le texte avec une souris ou un stylet. Avec un doigt, appuyez longuement puis faites glisser. Un double-clic sélectionne un mot.', 'de': 'ziehen Sie mit Maus oder Stift über den Text. Mit dem Finger: gedrückt halten, dann ziehen. Ein Doppelklick wählt ein Wort aus.', 'es': 'arrastra sobre el texto con un ratón o un lápiz. Con el dedo, mantén pulsado y luego arrastra. Un doble clic selecciona una palabra.', 'it': 'trascina sul testo con il mouse o la penna. Con un dito, tieni premuto e poi trascina. Un doppio clic seleziona una parola.'},
    'Toolbar:': {'nl': 'Werkbalk:', 'fr': "Barre d'outils :", 'de': 'Werkzeugleiste:', 'es': 'Barra de herramientas:', 'it': 'Barra degli strumenti:'},
    'copy, four highlight colours, note, read aloud, meaning (dictionary) and remove. The ••• button selects the whole sentence or paragraph.': {'nl': 'kopiëren, vier markeerkleuren, notitie, voorlezen, betekenis (woordenboek) en verwijderen. De knop ••• selecteert de hele zin of alinea.', 'fr': 'copier, quatre couleurs de surlignage, note, lecture, sens (dictionnaire) et supprimer. Le bouton ••• sélectionne toute la phrase ou le paragraphe.', 'de': 'kopieren, vier Markierfarben, Notiz, vorlesen, Bedeutung (Wörterbuch) und entfernen. Die Taste ••• wählt den ganzen Satz oder Absatz aus.', 'es': 'copiar, cuatro colores de resaltado, nota, leer, significado (diccionario) y quitar. El botón ••• selecciona la frase o el párrafo entero.', 'it': 'copia, quattro colori di evidenziazione, nota, leggi, significato (dizionario) e rimuovi. Il pulsante ••• seleziona tutta la frase o il paragrafo.'},
    'Stop selecting:': {'nl': 'Stoppen met selecteren:', 'fr': 'Arrêter la sélection :', 'de': 'Auswahl beenden:', 'es': 'Dejar de seleccionar:', 'it': 'Smettere di selezionare:'},
    'click anywhere else or press Esc.': {'nl': 'klik ergens anders of druk op Esc.', 'fr': 'cliquez ailleurs ou appuyez sur Échap.', 'de': 'klicken Sie woanders hin oder drücken Sie Esc.', 'es': 'haz clic en otro sitio o pulsa Esc.', 'it': 'fai clic altrove o premi Esc.'},
    'Undo:': {'nl': 'Ongedaan maken:', 'fr': 'Annuler :', 'de': 'Rückgängig:', 'es': 'Deshacer:', 'it': 'Annulla:'},
    'after you highlight or remove something, Undo appears at the bottom.': {'nl': "na markeren of verwijderen verschijnt onderaan 'Ongedaan maken'.", 'fr': 'après un surlignage ou une suppression, « Annuler » apparaît en bas.', 'de': 'nach dem Markieren oder Entfernen erscheint unten „Rückgängig“.', 'es': 'después de resaltar o quitar algo, aparece «Deshacer» abajo.', 'it': 'dopo aver evidenziato o rimosso qualcosa, in basso compare «Annulla».'},
    'Highlighter:': {'nl': 'Markeerstift:', 'fr': 'Surligneur :', 'de': 'Textmarker:', 'es': 'Marcador:', 'it': 'Evidenziatore:'},
    'switch it on to mark text just by dragging over it.': {'nl': 'zet hem aan om tekst te markeren door er gewoon over te slepen.', 'fr': 'activez-le pour surligner du texte simplement en glissant dessus.', 'de': 'schalten Sie ihn ein, um Text einfach durch Darüberziehen zu markieren.', 'es': 'actívalo para resaltar texto solo con arrastrar sobre él.', 'it': 'attivalo per evidenziare il testo semplicemente trascinandoci sopra.'},
    'Notes:': {'nl': 'Notities:', 'fr': 'Notes :', 'de': 'Notizen:', 'es': 'Notas:', 'it': 'Note:'},
    'type a note or speak it (Windows voice typing). The notes button lists all highlights and notes, and saves them as a Word document.': {'nl': 'typ een notitie of spreek ze in (Windows-spraakinvoer). De knop Notities toont alle markeringen en notities, en bewaart ze als Word-document.', 'fr': 'tapez une note ou dictez-la (saisie vocale Windows). Le bouton Notes liste tous les surlignages et notes, et les enregistre en document Word.', 'de': 'tippen Sie eine Notiz oder sprechen Sie sie ein (Windows-Spracheingabe). Die Taste Notizen listet alle Markierungen und Notizen und speichert sie als Word-Dokument.', 'es': 'escribe una nota o díctala (dictado de Windows). El botón Notas muestra todos los resaltados y notas, y los guarda como documento de Word.', 'it': 'scrivi una nota o dettala (digitazione vocale di Windows). Il pulsante Note elenca tutte le evidenziazioni e le note, e le salva come documento Word.'},
    'Local-only:': {'nl': 'Alleen lokaal:', 'fr': 'Local uniquement :', 'de': 'Nur lokal:', 'es': 'Solo local:', 'it': 'Solo locale:'},
    'the default. Nothing from your document leaves this device.': {'nl': 'de standaard. Niets uit je document verlaat dit apparaat.', 'fr': 'le choix par défaut. Rien de votre document ne quitte cet appareil.', 'de': 'die Voreinstellung. Nichts aus Ihrem Dokument verlässt dieses Gerät.', 'es': 'la opción predeterminada. Nada de tu documento sale de este dispositivo.', 'it': "l'impostazione predefinita. Niente del tuo documento lascia questo dispositivo."},
    'AI-assisted:': {'nl': 'AI-ondersteund:', 'fr': 'Assisté par IA :', 'de': 'KI-gestützt:', 'es': 'Asistido por IA:', 'it': 'Assistito da IA:'},
    'AI checks uncertain citations and OCR words, and makes summaries in Focus mode when you ask. Summaries are marked as made by AI.': {'nl': 'AI kijkt twijfelachtige verwijzingen en OCR-woorden na, en maakt op verzoek samenvattingen in de focusmodus. Samenvattingen zijn gemarkeerd als gemaakt door AI.', 'fr': "l'IA vérifie les citations et mots OCR incertains, et fait des résumés en mode concentration quand vous le demandez. Les résumés sont marqués comme créés par l'IA.", 'de': 'KI prüft unsichere Zitate und OCR-Wörter und erstellt auf Wunsch Zusammenfassungen im Fokusmodus. Zusammenfassungen sind als von KI erstellt markiert.', 'es': 'la IA revisa citas y palabras OCR dudosas, y hace resúmenes en el modo concentración cuando lo pides. Los resúmenes aparecen marcados como hechos por IA.', 'it': "l'IA controlla citazioni e parole OCR incerte, e crea riassunti in modalità concentrazione quando lo chiedi. I riassunti sono segnati come creati dall'IA."},
    'API keys:': {'nl': 'API-sleutels:', 'fr': 'Clés API :', 'de': 'API-Schlüssel:', 'es': 'Claves API:', 'it': 'Chiavi API:'},
    'add a key with a name, test the connection, and remove it with the cross.': {'nl': 'voeg een sleutel toe met een naam, test de verbinding, en verwijder hem met het kruisje.', 'fr': 'ajoutez une clé avec un nom, testez la connexion et supprimez-la avec la croix.', 'de': 'fügen Sie einen Schlüssel mit Namen hinzu, testen Sie die Verbindung und entfernen Sie ihn mit dem Kreuz.', 'es': 'añade una clave con un nombre, prueba la conexión y quítala con la cruz.', 'it': 'aggiungi una chiave con un nome, prova la connessione e rimuovila con la croce.'},
    'Privacy log:': {'nl': 'Privacylogboek:', 'fr': 'Journal de confidentialité :', 'de': 'Datenschutzprotokoll:', 'es': 'Registro de privacidad:', 'it': 'Registro della privacy:'},
    'every request is listed with the exact text that was sent.': {'nl': 'elk verzoek staat erin, met de exacte tekst die verstuurd is.', 'fr': 'chaque requête y figure, avec le texte exact qui a été envoyé.', 'de': 'jede Anfrage steht darin, mit dem genauen Text, der gesendet wurde.', 'es': 'cada solicitud aparece con el texto exacto que se envió.', 'it': 'ogni richiesta è elencata con il testo esatto che è stato inviato.'},
    'Appearance:': {'nl': 'Weergave:', 'fr': 'Apparence :', 'de': 'Darstellung:', 'es': 'Apariencia:', 'it': 'Aspetto:'},
    'Space': {'nl': 'Spatie', 'fr': 'Espace', 'de': 'Leertaste', 'es': 'Espacio', 'it': 'Spazio'},
    'app language, app font, dark mode, high-contrast colours and app text size. These only change the app, not your documents.': {'nl': 'app-taal, lettertype van de app, donkere modus, kleuren met hoog contrast en tekstgrootte van de app. Ze veranderen alleen de app, niet je documenten.', 'fr': "langue de l'application, police de l'application, mode sombre, couleurs à contraste élevé et taille du texte de l'application. Cela ne change que l'application, pas vos documents.", 'de': 'App-Sprache, App-Schrift, dunkler Modus, kontrastreiche Farben und Textgröße der App. Das ändert nur die App, nicht Ihre Dokumente.', 'es': 'idioma de la aplicación, fuente de la aplicación, modo oscuro, colores de alto contraste y tamaño del texto de la aplicación. Solo cambian la aplicación, no tus documentos.', 'it': "lingua dell'app, carattere dell'app, modalità scura, colori ad alto contrasto e dimensione del testo dell'app. Cambiano solo l'app, non i tuoi documenti."},
    'App font': {'nl': 'Lettertype van de app', 'fr': "Police de l'application", 'de': 'App-Schrift', 'es': 'Fuente de la aplicación', 'it': "Carattere dell'app"},
    "Changes the font of the app's menus and buttons. The font of your converted documents is chosen in the Convert tab.": {'nl': "Verandert het lettertype van de menu's en knoppen van de app. Het lettertype van je omgezette documenten kies je in het tabblad Omzetten.", 'fr': "Change la police des menus et boutons de l'application. La police de vos documents convertis se choisit dans l'onglet Convertir.", 'de': 'Ändert die Schrift der Menüs und Schaltflächen der App. Die Schrift Ihrer umgewandelten Dokumente wählen Sie im Reiter Umwandeln.', 'es': 'Cambia la fuente de los menús y botones de la aplicación. La fuente de tus documentos convertidos se elige en la pestaña Convertir.', 'it': "Cambia il carattere dei menu e dei pulsanti dell'app. Il carattere dei documenti convertiti si sceglie nella scheda Converti."},
    'Use this font in the app': {'nl': 'Dit lettertype in de app gebruiken', 'fr': "Utiliser cette police dans l'application", 'de': 'Diese Schrift in der App verwenden', 'es': 'Usar esta fuente en la aplicación', 'it': "Usa questo carattere nell'app"},
    'Atkinson Hyperlegible · clear, distinct letters (default)': {'nl': 'Atkinson Hyperlegible · duidelijke, goed te onderscheiden letters (standaard)', 'fr': 'Atkinson Hyperlegible · lettres claires et bien distinctes (par défaut)', 'de': 'Atkinson Hyperlegible · klare, gut unterscheidbare Buchstaben (Standard)', 'es': 'Atkinson Hyperlegible · letras claras y bien distintas (predeterminada)', 'it': 'Atkinson Hyperlegible · lettere chiare e ben distinte (predefinito)'},
    "Heavier letter bottoms, so letters don't flip": {'nl': 'Zwaardere onderkant van de letters, zodat ze niet omdraaien', 'fr': "Bas des lettres plus épais, pour qu'elles ne se retournent pas", 'de': 'Schwerere Buchstabenunterseiten, damit Buchstaben nicht kippen', 'es': 'Parte baja de las letras más gruesa, para que no se den la vuelta', 'it': 'Base delle lettere più pesante, così non si capovolgono'},
    'Arial-style': {'nl': 'Zoals Arial', 'fr': 'Style Arial', 'de': 'Arial-Stil', 'es': 'Estilo Arial', 'it': 'Stile Arial'},
    'Liberation Sans · plain and familiar': {'nl': 'Liberation Sans · eenvoudig en vertrouwd', 'fr': 'Liberation Sans · simple et familière', 'de': 'Liberation Sans · schlicht und vertraut', 'es': 'Liberation Sans · sencilla y familiar', 'it': 'Liberation Sans · semplice e familiare'},
    'Verdana-style': {'nl': 'Zoals Verdana', 'fr': 'Style Verdana', 'de': 'Verdana-Stil', 'es': 'Estilo Verdana', 'it': 'Stile Verdana'},
    'DejaVu Sans · wide letters, open spacing': {'nl': 'DejaVu Sans · brede letters, ruime spatiëring', 'fr': 'DejaVu Sans · lettres larges, espacement aéré', 'de': 'DejaVu Sans · breite Buchstaben, offene Abstände', 'es': 'DejaVu Sans · letras anchas, espaciado amplio', 'it': 'DejaVu Sans · lettere larghe, spaziatura ampia'},
    'OpenDyslexic': {'nl': 'OpenDyslexic', 'fr': 'OpenDyslexic', 'de': 'OpenDyslexic', 'es': 'OpenDyslexic', 'it': 'OpenDyslexic'},
    'One page at a time (click to scroll instead)': {'nl': 'Eén pagina tegelijk (klik om te scrollen)', 'fr': 'Une page à la fois (cliquez pour faire défiler)', 'de': 'Eine Seite nach der anderen (klicken zum Scrollen)', 'es': 'Una página cada vez (haz clic para desplazarte)', 'it': 'Una pagina alla volta (fai clic per scorrere)'},
    'Scrolling pages (click for one page at a time)': {'nl': "Scrollende pagina's (klik voor één pagina tegelijk)", 'fr': 'Pages qui défilent (cliquez pour une page à la fois)', 'de': 'Scrollende Seiten (klicken für eine Seite nach der anderen)', 'es': 'Páginas con desplazamiento (haz clic para ver una página cada vez)', 'it': 'Pagine a scorrimento (fai clic per una pagina alla volta)'},
    'Reading settings: text, spacing and page colour': {'nl': 'Leesinstellingen: tekst, witruimte en paginakleur', 'fr': 'Réglages de lecture : texte, espacement et couleur de page', 'de': 'Leseeinstellungen: Text, Abstände und Seitenfarbe', 'es': 'Ajustes de lectura: texto, espaciado y color de página', 'it': 'Impostazioni di lettura: testo, spaziatura e colore della pagina'},
    'Reading settings:': {'nl': 'Leesinstellingen:', 'fr': 'Réglages de lecture :', 'de': 'Leseeinstellungen:', 'es': 'Ajustes de lectura:', 'it': 'Impostazioni di lettura:'},
    'font, text size, spacing, and the page colour (white, cream, blue, green, grey or dark).': {'nl': 'lettertype, tekstgrootte, witruimte en de paginakleur (wit, crème, blauw, groen, grijs of donker).', 'fr': 'police, taille du texte, espacement et couleur de page (blanc, crème, bleu, vert, gris ou sombre).', 'de': 'Schrift, Textgröße, Abstände und die Seitenfarbe (weiß, creme, blau, grün, grau oder dunkel).', 'es': 'fuente, tamaño del texto, espaciado y el color de página (blanco, crema, azul, verde, gris u oscuro).', 'it': 'carattere, dimensione del testo, spaziatura e colore della pagina (bianco, crema, blu, verde, grigio o scuro).'},
    'Page buttons:': {'nl': 'Paginaknoppen:', 'fr': 'Boutons de page :', 'de': 'Seitentasten:', 'es': 'Botones de página:', 'it': 'Pulsanti della pagina:'},
    'always at the top right: scrolling or one page at a time, fit to the window, and a quarter turn.': {'nl': 'altijd rechtsboven: scrollen of één pagina tegelijk, passend in het venster, en een kwartslag draaien.', 'fr': 'toujours en haut à droite : défilement ou une page à la fois, ajuster à la fenêtre, et un quart de tour.', 'de': 'immer oben rechts: Scrollen oder eine Seite nach der anderen, ans Fenster anpassen und eine Vierteldrehung.', 'es': 'siempre arriba a la derecha: desplazamiento o una página cada vez, ajustar a la ventana y un cuarto de vuelta.', 'it': 'sempre in alto a destra: scorrimento o una pagina alla volta, adatta alla finestra e un quarto di giro.'},
    'Show the original': {'nl': 'Het origineel tonen', 'fr': "Afficher l'original", 'de': 'Original anzeigen', 'es': 'Mostrar el original', 'it': "Mostra l'originale"},
    'Previous page of the original': {'nl': 'Vorige pagina van het origineel', 'fr': "Page précédente de l'original", 'de': 'Vorherige Seite des Originals', 'es': 'Página anterior del original', 'it': "Pagina precedente dell'originale"},
    'Next page of the original': {'nl': 'Volgende pagina van het origineel', 'fr': "Page suivante de l'original", 'de': 'Nächste Seite des Originals', 'es': 'Página siguiente del original', 'it': "Pagina successiva dell'originale"},
    'page {n} of {total}': {'nl': 'pagina {n} van {total}', 'fr': 'page {n} sur {total}', 'de': 'Seite {n} von {total}', 'es': 'página {n} de {total}', 'it': 'pagina {n} di {total}'},
    'Fit to the panel': {'nl': 'Passend in het paneel', 'fr': 'Ajuster au panneau', 'de': 'An den Bereich anpassen', 'es': 'Ajustar al panel', 'it': 'Adatta al pannello'},
    'Wider': {'nl': 'Breder', 'fr': 'Plus large', 'de': 'Breiter', 'es': 'Más ancho', 'it': 'Più largo'},
    'Narrower': {'nl': 'Smaller', 'fr': 'Plus étroit', 'de': 'Schmaler', 'es': 'Más estrecho', 'it': 'Più stretto'},
    'Read only the original': {'nl': 'Alleen het origineel lezen', 'fr': "Lire seulement l'original", 'de': 'Nur das Original lesen', 'es': 'Leer solo el original', 'it': "Leggi solo l'originale"},
    'Back to the converted text': {'nl': 'Terug naar de omgezette tekst', 'fr': 'Retour au texte converti', 'de': 'Zurück zum umgewandelten Text', 'es': 'Volver al texto convertido', 'it': 'Torna al testo convertito'},
    'Good to know': {'nl': 'Goed om te weten', 'fr': 'Bon à savoir', 'de': 'Gut zu wissen', 'es': 'Conviene saber', 'it': 'Buono a sapersi'},
    'OK': {'nl': 'OK', 'fr': 'OK', 'de': 'OK', 'es': 'Aceptar', 'it': 'OK'},
    "Don't show this again": {'nl': 'Dit niet meer tonen', 'fr': 'Ne plus afficher', 'de': 'Nicht mehr anzeigen', 'es': 'No volver a mostrar', 'it': 'Non mostrare più'},
    'The converter changes how a document looks, never what it says: it does not rewrite, shorten or add to the text.': {'nl': 'De converter verandert hoe een document eruitziet, nooit wat erin staat: hij herschrijft, kort of vult de tekst niet aan.', 'fr': "Le convertisseur change l'apparence d'un document, jamais ce qu'il dit : il ne réécrit pas, ne raccourcit pas et n'ajoute rien au texte.", 'de': 'Der Konverter ändert, wie ein Dokument aussieht, nie, was darin steht: Er schreibt den Text nicht um, kürzt ihn nicht und fügt nichts hinzu.', 'es': 'El conversor cambia el aspecto de un documento, nunca lo que dice: no reescribe, no acorta ni añade nada al texto.', 'it': "Il convertitore cambia l'aspetto di un documento, mai ciò che dice: non riscrive, non accorcia e non aggiunge nulla al testo."},
    'It can make mistakes in the layout, for example the order of paragraphs, a heading, or where a picture or table goes.': {'nl': "Hij kan fouten maken in de opmaak, bijvoorbeeld in de volgorde van alinea's, een titel, of waar een afbeelding of tabel komt.", 'fr': "Il peut se tromper dans la mise en page, par exemple l'ordre des paragraphes, un titre, ou la place d'une image ou d'un tableau.", 'de': 'Beim Layout können Fehler passieren, zum Beispiel bei der Reihenfolge der Absätze, einer Überschrift oder der Stelle eines Bildes oder einer Tabelle.', 'es': 'Puede equivocarse en el diseño, por ejemplo en el orden de los párrafos, un título o el lugar de una imagen o tabla.', 'it': "Può sbagliare l'impaginazione, per esempio l'ordine dei paragrafi, un titolo o la posizione di un'immagine o di una tabella."},
    'Scanned pages are read by text recognition, which can misread a word; uncertain words are shown for you to check.': {'nl': "Gescande pagina's worden gelezen met tekstherkenning, die een woord verkeerd kan lezen; twijfelachtige woorden worden getoond zodat je ze kunt nakijken.", 'fr': 'Les pages scannées sont lues par reconnaissance de texte, qui peut mal lire un mot ; les mots incertains vous sont montrés pour vérification.', 'de': 'Gescannte Seiten werden per Texterkennung gelesen, die ein Wort falsch lesen kann; unsichere Wörter werden Ihnen zur Prüfung gezeigt.', 'es': 'Las páginas escaneadas se leen con reconocimiento de texto, que puede leer mal una palabra; las palabras dudosas se muestran para que las revises.', 'it': 'Le pagine scansionate sono lette con il riconoscimento del testo, che può leggere male una parola; le parole incerte ti vengono mostrate da controllare.'},
    'When something looks wrong, compare with the original: the Both view, or Show the original in focus mode.': {'nl': 'Ziet iets er verkeerd uit, vergelijk dan met het origineel: de weergave Beide, of Het origineel tonen in de focusmodus.', 'fr': "Si quelque chose semble faux, comparez avec l'original : la vue Les deux, ou Afficher l'original en mode concentration.", 'de': 'Wenn etwas falsch aussieht, vergleichen Sie mit dem Original: die Ansicht Beide oder Original anzeigen im Fokusmodus.', 'es': 'Si algo parece incorrecto, compáralo con el original: la vista Ambos, o Mostrar el original en el modo concentración.', 'it': "Se qualcosa sembra sbagliato, confronta con l'originale: la vista Entrambi, oppure Mostra l'originale nella modalità concentrazione."},
    'AI check': {'nl': 'AI-controle', 'fr': 'Vérification IA', 'de': 'KI-Prüfung', 'es': 'Revisión con IA', 'it': 'Controllo IA'},
    'AI check: no conversion mistakes found.': {'nl': 'AI-controle: geen conversiefouten gevonden.', 'fr': 'Vérification IA : aucune erreur de conversion trouvée.', 'de': 'KI-Prüfung: keine Umwandlungsfehler gefunden.', 'es': 'Revisión con IA: no se encontraron errores de conversión.', 'it': 'Controllo IA: nessun errore di conversione trovato.'},
    'AI check: {n} possible conversion mistake(s) found.': {'nl': 'AI-controle: {n} mogelijke conversiefout(en) gevonden.', 'fr': 'Vérification IA : {n} erreur(s) de conversion possible(s) trouvée(s).', 'de': 'KI-Prüfung: {n} mögliche(r) Umwandlungsfehler gefunden.', 'es': 'Revisión con IA: {n} posible(s) error(es) de conversión.', 'it': 'Controllo IA: {n} possibile/i errore/i di conversione trovato/i.'},
    'AI: {reason}': {'nl': 'AI: {reason}', 'fr': 'IA : {reason}', 'de': 'KI: {reason}', 'es': 'IA: {reason}', 'it': 'IA: {reason}'},
    'Back to the settings': {'nl': 'Terug naar de instellingen', 'fr': 'Retour aux réglages', 'de': 'Zurück zu den Einstellungen', 'es': 'Volver a los ajustes', 'it': 'Torna alle impostazioni'},
    'Broken or joined word': {'nl': 'Gebroken of aaneengeschreven woord', 'fr': 'Mot coupé ou collé', 'de': 'Getrenntes oder zusammengezogenes Wort', 'es': 'Palabra partida o unida', 'it': 'Parola spezzata o unita'},
    'Check': {'nl': 'Controleren', 'fr': 'Vérifier', 'de': 'Prüfen', 'es': 'Revisar', 'it': 'Controlla'},
    'Check again': {'nl': 'Opnieuw controleren', 'fr': 'Vérifier à nouveau', 'de': 'Erneut prüfen', 'es': 'Revisar de nuevo', 'it': 'Controlla di nuovo'},
    'Check the whole document with AI?': {'nl': 'Het hele document met AI controleren?', 'fr': "Vérifier tout le document avec l'IA ?", 'de': 'Das ganze Dokument mit KI prüfen?', 'es': '¿Revisar todo el documento con IA?', 'it': "Controllare tutto il documento con l'IA?"},
    'Checking the document with AI...': {'nl': 'Het document wordt met AI gecontroleerd...', 'fr': "Vérification du document avec l'IA...", 'de': 'Das Dokument wird mit KI geprüft...', 'es': 'Revisando el documento con IA...', 'it': "Controllo del documento con l'IA..."},
    'E-mail addresses, links and long numbers are masked. Tables, pictures and the reference list are not sent. Everything sent is listed in the privacy log in AI settings. Your provider may charge for this.': {'nl': 'E-mailadressen, links en lange nummers worden afgeschermd. Tabellen, afbeeldingen en de literatuurlijst worden niet verstuurd. Alles wat verstuurd wordt, staat in het privacylogboek bij AI-instellingen. Je provider kan hiervoor kosten aanrekenen.', 'fr': 'Les adresses e-mail, les liens et les longs numéros sont masqués. Les tableaux, les images et la bibliographie ne sont pas envoyés. Tout ce qui est envoyé figure dans le journal de confidentialité des réglages IA. Votre fournisseur peut facturer cet usage.', 'de': 'E-Mail-Adressen, Links und lange Nummern werden unkenntlich gemacht. Tabellen, Bilder und das Literaturverzeichnis werden nicht gesendet. Alles Gesendete steht im Datenschutzprotokoll unter KI-Einstellungen. Ihr Anbieter kann dafür Kosten berechnen.', 'es': 'Las direcciones de correo, los enlaces y los números largos se ocultan. Las tablas, las imágenes y la bibliografía no se envían. Todo lo enviado aparece en el registro de privacidad de los ajustes de IA. Tu proveedor puede cobrar por ello.', 'it': 'Indirizzi e-mail, link e numeri lunghi vengono mascherati. Tabelle, immagini e bibliografia non vengono inviate. Tutto ciò che viene inviato è elencato nel registro della privacy nelle impostazioni IA. Il tuo fornitore può addebitare questo uso.'},
    'Fix': {'nl': 'Herstellen', 'fr': 'Corriger', 'de': 'Beheben', 'es': 'Corregir', 'it': 'Correggi'},
    'Fix all broken words ({n})': {'nl': 'Alle gebroken woorden herstellen ({n})', 'fr': 'Corriger tous les mots coupés ({n})', 'de': 'Alle getrennten Wörter beheben ({n})', 'es': 'Corregir todas las palabras partidas ({n})', 'it': 'Correggi tutte le parole spezzate ({n})'},
    'Fixed': {'nl': 'Hersteld', 'fr': 'Corrigé', 'de': 'Behoben', 'es': 'Corregido', 'it': 'Corretto'},
    'Header, footer or page number in the text': {'nl': 'Kop- of voettekst of paginanummer in de tekst', 'fr': 'En-tête, pied de page ou numéro de page dans le texte', 'de': 'Kopf-, Fußzeile oder Seitenzahl im Text', 'es': 'Encabezado, pie o número de página en el texto', 'it': 'Intestazione, piè di pagina o numero di pagina nel testo'},
    'Heading run into the text': {'nl': 'Titel vastgeplakt aan de tekst', 'fr': 'Titre collé au texte', 'de': 'Überschrift im Fließtext', 'es': 'Título pegado al texto', 'it': 'Titolo attaccato al testo'},
    'Hide it, like other headers and footers': {'nl': 'Verbergen, zoals andere kop- en voetteksten', 'fr': 'Le masquer, comme les autres en-têtes et pieds de page', 'de': 'Ausblenden wie andere Kopf- und Fußzeilen', 'es': 'Ocultarlo, como otros encabezados y pies', 'it': 'Nascondilo, come le altre intestazioni e piè di pagina'},
    'Let the AI read the converted text and list conversion mistakes; you choose what to fix': {'nl': 'Laat de AI de omgezette tekst lezen en conversiefouten opsommen; jij kiest wat hersteld wordt', 'fr': "L'IA lit le texte converti et liste les erreurs de conversion ; vous choisissez ce qui est corrigé", 'de': 'Die KI liest den umgewandelten Text und listet Umwandlungsfehler auf; Sie wählen, was behoben wird', 'es': 'La IA lee el texto convertido y enumera los errores de conversión; tú eliges qué corregir', 'it': "L'IA legge il testo convertito ed elenca gli errori di conversione; scegli tu cosa correggere"},
    'Make it a heading': {'nl': 'Er een titel van maken', 'fr': 'En faire un titre', 'de': 'Zur Überschrift machen', 'es': 'Convertirlo en título', 'it': 'Rendilo un titolo'},
    'Make it normal text': {'nl': 'Er gewone tekst van maken', 'fr': 'En faire du texte normal', 'de': 'Zu normalem Text machen', 'es': 'Convertirlo en texto normal', 'it': 'Rendilo testo normale'},
    'Misread in the scan': {'nl': 'Verkeerd gelezen in de scan', 'fr': 'Mal lu dans le scan', 'de': 'Im Scan falsch gelesen', 'es': 'Mal leído en el escaneo', 'it': 'Letto male nella scansione'},
    'Not a heading': {'nl': 'Geen titel', 'fr': 'Pas un titre', 'de': 'Keine Überschrift', 'es': 'No es un título', 'it': 'Non è un titolo'},
    'Only fixes that change nothing but spaces and hyphens': {'nl': 'Alleen herstellingen die niets anders veranderen dan spaties en koppeltekens', 'fr': "Seulement les corrections qui ne changent que des espaces et des traits d'union", 'de': 'Nur Korrekturen, die nichts als Leerzeichen und Bindestriche ändern', 'es': 'Solo correcciones que cambian únicamente espacios y guiones', 'it': 'Solo correzioni che cambiano soltanto spazi e trattini'},
    'Remove it from the text': {'nl': 'Uit de tekst verwijderen', 'fr': 'Le retirer du texte', 'de': 'Aus dem Text entfernen', 'es': 'Quitarlo del texto', 'it': 'Toglilo dal testo'},
    'Show': {'nl': 'Tonen', 'fr': 'Afficher', 'de': 'Zeigen', 'es': 'Mostrar', 'it': 'Mostra'},
    'Show the text that will be sent': {'nl': 'De tekst tonen die verstuurd wordt', 'fr': 'Afficher le texte qui sera envoyé', 'de': 'Den Text zeigen, der gesendet wird', 'es': 'Mostrar el texto que se enviará', 'it': 'Mostra il testo che verrà inviato'},
    'Show this page in the preview': {'nl': 'Deze pagina tonen in de voorvertoning', 'fr': "Afficher cette page dans l'aperçu", 'de': 'Diese Seite in der Vorschau zeigen', 'es': 'Mostrar esta página en la vista previa', 'it': "Mostra questa pagina nell'anteprima"},
    'Text in the wrong place': {'nl': 'Tekst op de verkeerde plaats', 'fr': 'Texte au mauvais endroit', 'de': 'Text an der falschen Stelle', 'es': 'Texto en el lugar equivocado', 'it': 'Testo nel posto sbagliato'},
    'The AI check failed; nothing was changed.': {'nl': 'De AI-controle is mislukt; er is niets veranderd.', 'fr': "La vérification IA a échoué ; rien n'a été modifié.", 'de': 'Die KI-Prüfung ist fehlgeschlagen; es wurde nichts geändert.', 'es': 'La revisión con IA falló; no se cambió nada.', 'it': 'Il controllo IA non è riuscito; non è stato cambiato nulla.'},
    'The AI check needs AI: choose AI-assisted and add an API key in AI settings.': {'nl': 'De AI-controle heeft AI nodig: kies AI-ondersteund en voeg een API-sleutel toe bij AI-instellingen.', 'fr': "La vérification IA a besoin de l'IA : choisissez Assisté par IA et ajoutez une clé API dans les réglages IA.", 'de': 'Die KI-Prüfung braucht KI: Wählen Sie KI-gestützt und fügen Sie unter KI-Einstellungen einen API-Schlüssel hinzu.', 'es': 'La revisión con IA necesita IA: elige Asistido por IA y añade una clave API en los ajustes de IA.', 'it': "Il controllo IA richiede l'IA: scegli Assistito dall'IA e aggiungi una chiave API nelle impostazioni IA."},
    'The AI found no conversion mistakes.': {'nl': 'De AI vond geen conversiefouten.', 'fr': "L'IA n'a trouvé aucune erreur de conversion.", 'de': 'Die KI hat keine Umwandlungsfehler gefunden.', 'es': 'La IA no encontró errores de conversión.', 'it': "L'IA non ha trovato errori di conversione."},
    "The AI reads the converted text and lists places where the conversion may have gone wrong: broken or joined words, headers or page numbers in the text, headings run into the text, and text in the wrong place. It does not look for the author's own spelling mistakes. Nothing is changed until you choose Fix, and every fix can be undone.": {'nl': 'De AI leest de omgezette tekst en somt plaatsen op waar de conversie mogelijk misging: gebroken of aaneengeschreven woorden, kop- of voetteksten of paginanummers in de tekst, titels die aan de tekst vastzitten, en tekst op de verkeerde plaats. Ze zoekt niet naar spelfouten van de auteur zelf. Er verandert niets tot je Herstellen kiest, en elke herstelling kan ongedaan gemaakt worden.', 'fr': "L'IA lit le texte converti et liste les endroits où la conversion a pu mal se passer : mots coupés ou collés, en-têtes ou numéros de page dans le texte, titres collés au texte et texte au mauvais endroit. Elle ne cherche pas les fautes d'orthographe de l'auteur. Rien n'est modifié tant que vous ne choisissez pas Corriger, et chaque correction peut être annulée.", 'de': 'Die KI liest den umgewandelten Text und listet Stellen auf, an denen die Umwandlung schiefgegangen sein kann: getrennte oder zusammengezogene Wörter, Kopfzeilen oder Seitenzahlen im Text, Überschriften im Fließtext und Text an der falschen Stelle. Sie sucht nicht nach Rechtschreibfehlern des Autors. Nichts wird geändert, bis Sie Beheben wählen, und jede Korrektur lässt sich rückgängig machen.', 'es': 'La IA lee el texto convertido y enumera los lugares donde la conversión pudo fallar: palabras partidas o unidas, encabezados o números de página en el texto, títulos pegados al texto y texto en el lugar equivocado. No busca faltas de ortografía del propio autor. No se cambia nada hasta que eliges Corregir, y cada corrección se puede deshacer.', 'it': "L'IA legge il testo convertito ed elenca i punti in cui la conversione può essere andata storta: parole spezzate o unite, intestazioni o numeri di pagina nel testo, titoli attaccati al testo e testo nel posto sbagliato. Non cerca gli errori di ortografia dell'autore. Nulla cambia finché non scegli Correggi, e ogni correzione si può annullare."},
    'The app cannot move text: compare with the original, or read only the original in focus mode.': {'nl': 'De app kan geen tekst verplaatsen: vergelijk met het origineel, of lees alleen het origineel in de focusmodus.', 'fr': "L'application ne peut pas déplacer du texte : comparez avec l'original, ou lisez seulement l'original en mode concentration.", 'de': 'Die App kann keinen Text verschieben: Vergleichen Sie mit dem Original oder lesen Sie nur das Original im Fokusmodus.', 'es': 'La aplicación no puede mover texto: compáralo con el original, o lee solo el original en el modo concentración.', 'it': "L'app non può spostare il testo: confronta con l'originale, oppure leggi solo l'originale nella modalità concentrazione."},
    'This document has no text to check.': {'nl': 'Dit document heeft geen tekst om te controleren.', 'fr': "Ce document n'a pas de texte à vérifier.", 'de': 'Dieses Dokument hat keinen Text zum Prüfen.', 'es': 'Este documento no tiene texto que revisar.', 'it': 'Questo documento non ha testo da controllare.'},
    'This sends the whole text of the document to {provider} ({model}): about {words} words in {n} request(s).': {'nl': 'Dit stuurt de hele tekst van het document naar {provider} ({model}): ongeveer {words} woorden in {n} verzoek(en).', 'fr': 'Cela envoie tout le texte du document à {provider} ({model}) : environ {words} mots en {n} requête(s).', 'de': 'Dabei wird der ganze Text des Dokuments an {provider} ({model}) gesendet: etwa {words} Wörter in {n} Anfrage(n).', 'es': 'Esto envía todo el texto del documento a {provider} ({model}): unas {words} palabras en {n} solicitud(es).', 'it': 'Questo invia tutto il testo del documento a {provider} ({model}): circa {words} parole in {n} richiesta/e.'},
    'This text was already changed (by you or another fix); undo that first.': {'nl': 'Deze tekst is al veranderd (door jou of een andere herstelling); maak dat eerst ongedaan.', 'fr': "Ce texte a déjà été modifié (par vous ou une autre correction) ; annulez d'abord cela.", 'de': 'Dieser Text wurde bereits geändert (von Ihnen oder einer anderen Korrektur); machen Sie das zuerst rückgängig.', 'es': 'Este texto ya se cambió (por ti o por otra corrección); deshazlo primero.', 'it': "Questo testo è già stato cambiato (da te o da un'altra correzione); annulla prima quello."},
    'Undo all fixes': {'nl': 'Alle herstellingen ongedaan maken', 'fr': 'Annuler toutes les corrections', 'de': 'Alle Korrekturen rückgängig', 'es': 'Deshacer todas las correcciones', 'it': 'Annulla tutte le correzioni'},
    "{n} part(s) of the document could not be checked (the AI's answer was unreadable). Check again to retry them.": {'nl': '{n} deel/delen van het document kon(den) niet gecontroleerd worden (het antwoord van de AI was onleesbaar). Controleer opnieuw om het nog eens te proberen.', 'fr': "{n} partie(s) du document n'a/ont pas pu être vérifiée(s) (la réponse de l'IA était illisible). Vérifiez à nouveau pour réessayer.", 'de': '{n} Teil(e) des Dokuments konnte(n) nicht geprüft werden (die Antwort der KI war unlesbar). Prüfen Sie erneut, um es noch einmal zu versuchen.', 'es': '{n} parte(s) del documento no se pudo/pudieron revisar (la respuesta de la IA era ilegible). Revisa de nuevo para reintentarlo.', 'it': "{n} parte/i del documento non è/sono stata/e controllata/e (la risposta dell'IA era illeggibile). Controlla di nuovo per riprovare."},
    '{n} possible conversion mistake(s) found. Nothing is changed until you choose Fix; every fix can be undone.': {'nl': '{n} mogelijke conversiefout(en) gevonden. Er verandert niets tot je Herstellen kiest; elke herstelling kan ongedaan gemaakt worden.', 'fr': "{n} erreur(s) de conversion possible(s) trouvée(s). Rien n'est modifié tant que vous ne choisissez pas Corriger ; chaque correction peut être annulée.", 'de': '{n} mögliche(r) Umwandlungsfehler gefunden. Nichts wird geändert, bis Sie Beheben wählen; jede Korrektur lässt sich rückgängig machen.', 'es': '{n} posible(s) error(es) de conversión. No se cambia nada hasta que eliges Corregir; cada corrección se puede deshacer.', 'it': '{n} possibile/i errore/i di conversione trovato/i. Nulla cambia finché non scegli Correggi; ogni correzione si può annullare.'},
    'AI check:': {'nl': 'AI-controle:', 'fr': 'Vérification IA :', 'de': 'KI-Prüfung:', 'es': 'Revisión con IA:', 'it': 'Controllo IA:'},
    'the AI check button on the Convert screen lets the AI read the whole converted text and list conversion mistakes. You choose what to fix, and can undo it.': {'nl': 'met de knop AI-controle op het scherm Omzetten leest de AI de hele omgezette tekst en somt conversiefouten op. Jij kiest wat hersteld wordt, en kunt het ongedaan maken.', 'fr': "le bouton Vérification IA de l'écran Convertir fait lire tout le texte converti par l'IA, qui liste les erreurs de conversion. Vous choisissez ce qui est corrigé et pouvez l'annuler.", 'de': 'mit der Taste KI-Prüfung im Bildschirm Umwandeln liest die KI den ganzen umgewandelten Text und listet Umwandlungsfehler auf. Sie wählen, was behoben wird, und können es rückgängig machen.', 'es': 'el botón Revisión con IA de la pantalla Convertir hace que la IA lea todo el texto convertido y enumere los errores de conversión. Tú eliges qué corregir y puedes deshacerlo.', 'it': "il pulsante Controllo IA nella schermata Converti fa leggere all'IA tutto il testo convertito ed elencare gli errori di conversione. Scegli tu cosa correggere, e puoi annullarlo."},
    'Let AI fix the order of this page': {'nl': 'Laat AI de volgorde van deze pagina herstellen', 'fr': "Laisser l'IA corriger l'ordre de cette page", 'de': 'Die Reihenfolge dieser Seite von der KI korrigieren lassen', 'es': 'Dejar que la IA corrija el orden de esta página', 'it': "Lascia che l'IA corregga l'ordine di questa pagina"},
    'The AI puts the pieces of the page in reading order; you can undo it': {'nl': 'De AI zet de stukken van de pagina in leesvolgorde; je kunt het ongedaan maken', 'fr': "L'IA met les morceaux de la page dans l'ordre de lecture ; vous pouvez l'annuler", 'de': 'Die KI bringt die Teile der Seite in Lesereihenfolge; Sie können es rückgängig machen', 'es': 'La IA pone las partes de la página en orden de lectura; puedes deshacerlo', 'it': "L'IA mette le parti della pagina in ordine di lettura; puoi annullarlo"},
    "Page {n} is read in the AI's order.": {'nl': 'Pagina {n} wordt gelezen in de volgorde van de AI.', 'fr': "La page {n} est lue dans l'ordre de l'IA.", 'de': 'Seite {n} wird in der Reihenfolge der KI gelesen.', 'es': 'La página {n} se lee en el orden de la IA.', 'it': "La pagina {n} viene letta nell'ordine dell'IA."},
    'Let AI fix the order of page {n}?': {'nl': 'AI de volgorde van pagina {n} laten herstellen?', 'fr': "Laisser l'IA corriger l'ordre de la page {n} ?", 'de': 'Die Reihenfolge von Seite {n} von der KI korrigieren lassen?', 'es': '¿Dejar que la IA corrija el orden de la página {n}?', 'it': "Lasciare che l'IA corregga l'ordine della pagina {n}?"},
    'This sends where each piece of page {n} is, its type size and its first and last words (e-mail addresses, links and long numbers masked) to {provider}. The app then reads the page in the order the AI gives; you can undo it. The findings on this page are cleared: Check again checks the page anew.': {'nl': 'Dit stuurt naar {provider} waar elk stuk van pagina {n} staat, de lettergrootte en de eerste en laatste woorden (e-mailadressen, links en lange nummers afgeschermd). De app leest de pagina daarna in de volgorde die de AI geeft; je kunt het ongedaan maken. De bevindingen op deze pagina worden gewist: Opnieuw controleren controleert de pagina opnieuw.', 'fr': "Cela envoie à {provider} l'emplacement de chaque morceau de la page {n}, sa taille de caractère et ses premiers et derniers mots (adresses e-mail, liens et longs numéros masqués). L'application lit ensuite la page dans l'ordre donné par l'IA ; vous pouvez l'annuler. Les constats de cette page sont effacés : Vérifier à nouveau vérifie la page de nouveau.", 'de': 'Dabei wird an {provider} gesendet, wo jedes Teil von Seite {n} steht, seine Schriftgröße und seine ersten und letzten Wörter (E-Mail-Adressen, Links und lange Nummern unkenntlich). Die App liest die Seite dann in der Reihenfolge der KI; Sie können es rückgängig machen. Die Befunde auf dieser Seite werden gelöscht: Erneut prüfen prüft die Seite neu.', 'es': 'Esto envía a {provider} dónde está cada parte de la página {n}, su tamaño de letra y sus primeras y últimas palabras (correos, enlaces y números largos ocultos). La aplicación lee luego la página en el orden que da la IA; puedes deshacerlo. Los hallazgos de esta página se borran: Revisar de nuevo revisa la página otra vez.', 'it': "Questo invia a {provider} dove si trova ogni parte della pagina {n}, la dimensione del carattere e le prime e ultime parole (indirizzi e-mail, link e numeri lunghi mascherati). L'app legge poi la pagina nell'ordine dato dall'IA; puoi annullarlo. I risultati di questa pagina vengono cancellati: Controlla di nuovo controlla di nuovo la pagina."},
    'The AI gave no usable order; the page is unchanged.': {'nl': 'De AI gaf geen bruikbare volgorde; de pagina is niet veranderd.', 'fr': "L'IA n'a pas donné d'ordre utilisable ; la page est inchangée.", 'de': 'Die KI hat keine brauchbare Reihenfolge geliefert; die Seite bleibt unverändert.', 'es': 'La IA no dio un orden utilizable; la página no cambia.', 'it': "L'IA non ha dato un ordine utilizzabile; la pagina non cambia."},
    'Asking AI for the reading order of the page...': {'nl': 'De AI wordt gevraagd naar de leesvolgorde van de pagina...', 'fr': "Demande à l'IA de l'ordre de lecture de la page...", 'de': 'Die KI wird nach der Lesereihenfolge der Seite gefragt...', 'es': 'Preguntando a la IA el orden de lectura de la página...', 'it': "Richiesta all'IA dell'ordine di lettura della pagina..."},
    'Back to converting': {'nl': 'Terug naar omzetten', 'fr': 'Retour à la conversion', 'de': 'Zurück zum Umwandeln', 'es': 'Volver a convertir', 'it': 'Torna alla conversione'},
    'Before anything is sent, you see how much text goes to which provider.': {'nl': 'Voordat er iets verstuurd wordt, zie je hoeveel tekst naar welke provider gaat.', 'fr': 'Avant tout envoi, vous voyez quelle quantité de texte part vers quel fournisseur.', 'de': 'Bevor etwas gesendet wird, sehen Sie, wie viel Text an welchen Anbieter geht.', 'es': 'Antes de enviar nada, ves cuánto texto va a qué proveedor.', 'it': 'Prima di inviare qualsiasi cosa, vedi quanto testo va a quale fornitore.'},
    'Check and fix everything': {'nl': 'Alles controleren en herstellen', 'fr': 'Tout vérifier et corriger', 'de': 'Alles prüfen und beheben', 'es': 'Revisar y corregir todo', 'it': 'Controlla e correggi tutto'},
    'Check and fix everything with AI?': {'nl': 'Alles controleren en herstellen met AI?', 'fr': "Tout vérifier et corriger avec l'IA ?", 'de': 'Alles mit KI prüfen und beheben?', 'es': '¿Revisar y corregir todo con IA?', 'it': "Controllare e correggere tutto con l'IA?"},
    'Check and fix everything: the AI goes over all pages, puts pages with text in the wrong place in reading order, and the app makes every fix it found. Undo all puts everything back.': {'nl': "Alles controleren en herstellen: de AI gaat alle pagina's langs, zet pagina's met tekst op de verkeerde plaats in leesvolgorde, en de app voert elke gevonden herstelling uit. Alles ongedaan maken zet alles terug.", 'fr': "Tout vérifier et corriger : l'IA parcourt toutes les pages, remet dans l'ordre de lecture les pages dont du texte est mal placé, et l'application fait toutes les corrections trouvées. Tout annuler remet tout comme avant.", 'de': 'Alles prüfen und beheben: Die KI geht alle Seiten durch, bringt Seiten mit Text an der falschen Stelle in Lesereihenfolge, und die App führt jede gefundene Korrektur aus. Alles rückgängig stellt alles wieder her.', 'es': 'Revisar y corregir todo: la IA recorre todas las páginas, pone en orden de lectura las páginas con texto fuera de lugar y la aplicación hace todas las correcciones encontradas. Deshacer todo lo devuelve todo como estaba.', 'it': "Controlla e correggi tutto: l'IA passa tutte le pagine, mette in ordine di lettura le pagine con testo fuori posto e l'app applica ogni correzione trovata. Annulla tutto rimette tutto com'era."},
    'Check the document': {'nl': 'Het document controleren', 'fr': 'Vérifier le document', 'de': 'Das Dokument prüfen', 'es': 'Revisar el documento', 'it': 'Controlla il documento'},
    'Check the document: you see what was found, and choose what to fix.': {'nl': 'Het document controleren: je ziet wat er gevonden is, en kiest wat hersteld wordt.', 'fr': 'Vérifier le document : vous voyez ce qui a été trouvé et choisissez ce qui est corrigé.', 'de': 'Das Dokument prüfen: Sie sehen, was gefunden wurde, und wählen, was behoben wird.', 'es': 'Revisar el documento: ves lo que se encontró y eliges qué corregir.', 'it': 'Controlla il documento: vedi cosa è stato trovato e scegli cosa correggere.'},
    'Everything the AI check changed was undone.': {'nl': 'Alles wat de AI-controle veranderde, is ongedaan gemaakt.', 'fr': 'Tout ce que la vérification IA a modifié a été annulé.', 'de': 'Alles, was die KI-Prüfung geändert hat, wurde rückgängig gemacht.', 'es': 'Se deshizo todo lo que cambió la revisión con IA.', 'it': 'Tutto ciò che il controllo IA ha cambiato è stato annullato.'},
    'For each page with text in the wrong place, it also sends where each piece of the page is, its type size and its first and last words.': {'nl': 'Voor elke pagina met tekst op de verkeerde plaats stuurt het ook waar elk stuk van de pagina staat, de lettergrootte en de eerste en laatste woorden.', 'fr': "Pour chaque page dont du texte est mal placé, il envoie aussi l'emplacement de chaque morceau de la page, sa taille de caractère et ses premiers et derniers mots.", 'de': 'Für jede Seite mit Text an der falschen Stelle wird auch gesendet, wo jedes Teil der Seite steht, seine Schriftgröße und seine ersten und letzten Wörter.', 'es': 'Para cada página con texto fuera de lugar, también envía dónde está cada parte de la página, su tamaño de letra y sus primeras y últimas palabras.', 'it': 'Per ogni pagina con testo fuori posto invia anche dove si trova ogni parte della pagina, la dimensione del carattere e le prime e ultime parole.'},
    'The AI can put the pieces of this page in reading order; you can undo it.': {'nl': 'De AI kan de stukken van deze pagina in leesvolgorde zetten; je kunt het ongedaan maken.', 'fr': "L'IA peut remettre les morceaux de cette page dans l'ordre de lecture ; vous pouvez l'annuler.", 'de': 'Die KI kann die Teile dieser Seite in Lesereihenfolge bringen; Sie können es rückgängig machen.', 'es': 'La IA puede poner las partes de esta página en orden de lectura; puedes deshacerlo.', 'it': "L'IA può mettere le parti di questa pagina in ordine di lettura; puoi annullarlo."},
    'The AI checks the document, puts pages with text in the wrong place in reading order, and the app makes every fix; all of it can be undone': {'nl': "De AI controleert het document, zet pagina's met tekst op de verkeerde plaats in leesvolgorde, en de app voert elke herstelling uit; alles kan ongedaan gemaakt worden", 'fr': "L'IA vérifie le document, remet dans l'ordre de lecture les pages dont du texte est mal placé, et l'application fait toutes les corrections ; tout peut être annulé", 'de': 'Die KI prüft das Dokument, bringt Seiten mit Text an der falschen Stelle in Lesereihenfolge, und die App führt jede Korrektur aus; alles lässt sich rückgängig machen', 'es': 'La IA revisa el documento, pone en orden de lectura las páginas con texto fuera de lugar y la aplicación hace todas las correcciones; todo se puede deshacer', 'it': "L'IA controlla il documento, mette in ordine di lettura le pagine con testo fuori posto e l'app applica ogni correzione; tutto si può annullare"},
    'The AI goes over all pages: it checks the converted text, puts pages with text in the wrong place in reading order, and the app then makes every fix it found. Undo all puts everything back.': {'nl': "De AI gaat alle pagina's langs: ze controleert de omgezette tekst, zet pagina's met tekst op de verkeerde plaats in leesvolgorde, en de app voert daarna elke gevonden herstelling uit. Alles ongedaan maken zet alles terug.", 'fr': "L'IA parcourt toutes les pages : elle vérifie le texte converti, remet dans l'ordre de lecture les pages dont du texte est mal placé, puis l'application fait toutes les corrections trouvées. Tout annuler remet tout comme avant.", 'de': 'Die KI geht alle Seiten durch: Sie prüft den umgewandelten Text, bringt Seiten mit Text an der falschen Stelle in Lesereihenfolge, und die App führt danach jede gefundene Korrektur aus. Alles rückgängig stellt alles wieder her.', 'es': 'La IA recorre todas las páginas: revisa el texto convertido, pone en orden de lectura las páginas con texto fuera de lugar y después la aplicación hace todas las correcciones encontradas. Deshacer todo lo devuelve todo como estaba.', 'it': "L'IA passa tutte le pagine: controlla il testo convertito, mette in ordine di lettura le pagine con testo fuori posto e poi l'app applica ogni correzione trovata. Annulla tutto rimette tutto com'era."},
    'The AI made {n} fix(es) and put {pages} page(s) in reading order. Undo all puts everything back.': {'nl': "De AI voerde {n} herstelling(en) uit en zette {pages} pagina('s) in leesvolgorde. Alles ongedaan maken zet alles terug.", 'fr': "L'IA a fait {n} correction(s) et remis {pages} page(s) dans l'ordre de lecture. Tout annuler remet tout comme avant.", 'de': 'Die KI hat {n} Korrektur(en) ausgeführt und {pages} Seite(n) in Lesereihenfolge gebracht. Alles rückgängig stellt alles wieder her.', 'es': 'La IA hizo {n} corrección(es) y puso {pages} página(s) en orden de lectura. Deshacer todo lo devuelve todo como estaba.', 'it': "L'IA ha fatto {n} correzione/i e messo {pages} pagina/e in ordine di lettura. Annulla tutto rimette tutto com'era."},
    "The AI reads the converted text and lists places where the conversion may have gone wrong: broken or joined words, headers or page numbers in the text, headings run into the text, and text in the wrong place. It does not look for the author's own spelling mistakes.": {'nl': 'De AI leest de omgezette tekst en somt plaatsen op waar de conversie mogelijk misging: gebroken of aaneengeschreven woorden, kop- of voetteksten of paginanummers in de tekst, titels die aan de tekst vastzitten, en tekst op de verkeerde plaats. Ze zoekt niet naar spelfouten van de auteur zelf.', 'fr': "L'IA lit le texte converti et liste les endroits où la conversion a pu mal se passer : mots coupés ou collés, en-têtes ou numéros de page dans le texte, titres collés au texte et texte au mauvais endroit. Elle ne cherche pas les fautes d'orthographe de l'auteur.", 'de': 'Die KI liest den umgewandelten Text und listet Stellen auf, an denen die Umwandlung schiefgegangen sein kann: getrennte oder zusammengezogene Wörter, Kopfzeilen oder Seitenzahlen im Text, Überschriften im Fließtext und Text an der falschen Stelle. Sie sucht nicht nach Rechtschreibfehlern des Autors.', 'es': 'La IA lee el texto convertido y enumera los lugares donde la conversión pudo fallar: palabras partidas o unidas, encabezados o números de página en el texto, títulos pegados al texto y texto en el lugar equivocado. No busca faltas de ortografía del propio autor.', 'it': "L'IA legge il testo convertito ed elenca i punti in cui la conversione può essere andata storta: parole spezzate o unite, intestazioni o numeri di pagina nel testo, titoli attaccati al testo e testo nel posto sbagliato. Non cerca gli errori di ortografia dell'autore."},
    'The text was checked before: the earlier answers are used, nothing is sent again.': {'nl': 'De tekst werd al eerder gecontroleerd: de eerdere antwoorden worden gebruikt, er wordt niets opnieuw verstuurd.', 'fr': "Le texte a déjà été vérifié : les réponses précédentes sont utilisées, rien n'est renvoyé.", 'de': 'Der Text wurde schon geprüft: Die früheren Antworten werden verwendet, nichts wird erneut gesendet.', 'es': 'El texto ya se revisó: se usan las respuestas anteriores, no se vuelve a enviar nada.', 'it': 'Il testo è già stato controllato: si usano le risposte precedenti, non si invia nulla di nuovo.'},
    'Undo all': {'nl': 'Alles ongedaan maken', 'fr': 'Tout annuler', 'de': 'Alles rückgängig', 'es': 'Deshacer todo', 'it': 'Annulla tutto'},
    'What was done so far can be undone.': {'nl': 'Wat tot nu toe gedaan is, kan ongedaan gemaakt worden.', 'fr': 'Ce qui a déjà été fait peut être annulé.', 'de': 'Was bisher getan wurde, lässt sich rückgängig machen.', 'es': 'Lo hecho hasta ahora se puede deshacer.', 'it': 'Ciò che è stato fatto finora si può annullare.'},
    "This page is already read in the AI's order: compare with the original, or read only the original in focus mode.": {'nl': 'Deze pagina wordt al gelezen in de volgorde van de AI: vergelijk met het origineel, of lees alleen het origineel in de focusmodus.', 'fr': "Cette page est déjà lue dans l'ordre de l'IA : comparez avec l'original, ou lisez seulement l'original en mode concentration.", 'de': 'Diese Seite wird bereits in der Reihenfolge der KI gelesen: Vergleichen Sie mit dem Original oder lesen Sie nur das Original im Fokusmodus.', 'es': 'Esta página ya se lee en el orden de la IA: compárala con el original, o lee solo el original en el modo concentración.', 'it': "Questa pagina è già letta nell'ordine dell'IA: confronta con l'originale, oppure leggi solo l'originale nella modalità concentrazione."},
    'Articles, book chapters and scans all work. Change the layout on the left at any time.': {'nl': 'Artikels, boekhoofdstukken en scans werken allemaal. Pas de opmaak links op elk moment aan.', 'fr': 'Articles, chapitres de livres et scans fonctionnent tous. Modifiez la mise en page à gauche à tout moment.', 'de': 'Artikel, Buchkapitel und Scans funktionieren alle. Ändern Sie das Layout links jederzeit.', 'es': 'Artículos, capítulos de libros y escaneos funcionan todos. Cambia el diseño a la izquierda cuando quieras.', 'it': "Articoli, capitoli di libri e scansioni funzionano tutti. Cambia l'impaginazione a sinistra quando vuoi."},
    'How the app itself looks and works. The layout of your documents is set on the Convert screen.': {'nl': 'Hoe de app zelf eruitziet en werkt. De opmaak van je documenten stel je in op het scherm Omzetten.', 'fr': "L'apparence et le fonctionnement de l'application. La mise en page de vos documents se règle sur l'écran Convertir.", 'de': 'Wie die App selbst aussieht und funktioniert. Das Layout Ihrer Dokumente stellen Sie im Bildschirm Umwandeln ein.', 'es': 'Cómo se ve y funciona la propia aplicación. El diseño de tus documentos se ajusta en la pantalla Convertir.', 'it': "Come appare e funziona l'app. L'impaginazione dei tuoi documenti si imposta nella schermata Converti."},
    'On or off': {'nl': 'Aan of uit', 'fr': 'Activée ou non', 'de': 'An oder aus', 'es': 'Activada o no', 'it': 'Attiva o no'},
    'Open a PDF to start': {'nl': 'Open een pdf om te beginnen', 'fr': 'Ouvrez un PDF pour commencer', 'de': 'Öffnen Sie ein PDF, um zu beginnen', 'es': 'Abre un PDF para empezar', 'it': 'Apri un PDF per iniziare'},
    'The AI check button on the Convert screen reads the whole converted text and lists conversion mistakes; you choose what to fix.': {'nl': 'De knop AI-controle op het scherm Omzetten leest de hele omgezette tekst en somt conversiefouten op; jij kiest wat hersteld wordt.', 'fr': "Le bouton Vérification IA de l'écran Convertir lit tout le texte converti et liste les erreurs de conversion ; vous choisissez ce qui est corrigé.", 'de': 'Die Taste KI-Prüfung im Bildschirm Umwandeln liest den ganzen umgewandelten Text und listet Umwandlungsfehler auf; Sie wählen, was behoben wird.', 'es': 'El botón Revisión con IA de la pantalla Convertir lee todo el texto convertido y enumera los errores de conversión; tú eliges qué corregir.', 'it': 'Il pulsante Controllo IA nella schermata Converti legge tutto il testo convertito ed elenca gli errori di conversione; scegli tu cosa correggere.'},
    'The converted version appears here next to the original, so you can compare them. Your original file is never changed.': {'nl': 'De omgezette versie verschijnt hier naast het origineel, zodat je ze kunt vergelijken. Je originele bestand wordt nooit veranderd.', 'fr': "La version convertie apparaît ici à côté de l'original, pour que vous puissiez les comparer. Votre fichier original n'est jamais modifié.", 'de': 'Die umgewandelte Fassung erscheint hier neben dem Original, damit Sie vergleichen können. Ihre Originaldatei wird nie verändert.', 'es': 'La versión convertida aparece aquí junto al original, para que puedas compararlas. Tu archivo original nunca se modifica.', 'it': "La versione convertita appare qui accanto all'originale, così puoi confrontarle. Il tuo file originale non viene mai modificato."},
    # ---------------------------------------------------------------- focus mode loading screen, page pictures
    "Preparing your pages…": {"nl": "Je pagina's worden klaargezet…", "fr": "Préparation de vos pages…",
                              "de": "Deine Seiten werden vorbereitet…", "es": "Preparando tus páginas…",
                              "it": "Preparazione delle pagine…"},
    "The other pages follow while you read.": {
        "nl": "De andere pagina's volgen terwijl je leest.",
        "fr": "Les autres pages suivent pendant votre lecture.",
        "de": "Die übrigen Seiten folgen, während du liest.",
        "es": "Las demás páginas llegan mientras lees.",
        "it": "Le altre pagine arrivano mentre leggi."},
    "Focus mode keeps the pages it has drawn there too, so a document you open again shows at once.": {
        "nl": "De focusmodus bewaart daar ook de pagina's die hij heeft getekend, zodat een document dat je "
              "opnieuw opent meteen verschijnt.",
        "fr": "Le mode concentration y garde aussi les pages qu'il a dessinées : un document rouvert s'affiche "
              "tout de suite.",
        "de": "Der Fokusmodus speichert dort auch die gezeichneten Seiten, damit ein erneut geöffnetes Dokument "
              "sofort erscheint.",
        "es": "El modo concentración también guarda allí las páginas que ha dibujado, para que un documento "
              "que vuelves a abrir aparezca al instante.",
        "it": "La modalità concentrazione conserva lì anche le pagine già disegnate, così un documento riaperto "
              "compare subito."},
    "Clear saved page pictures": {"nl": "Bewaarde paginaweergaven wissen",
                                  "fr": "Effacer les images de pages enregistrées",
                                  "de": "Gespeicherte Seitenbilder löschen",
                                  "es": "Borrar las imágenes de páginas guardadas",
                                  "it": "Cancella le immagini delle pagine salvate"},
    "Saved page pictures cleared ({n}).": {"nl": "Bewaarde paginaweergaven gewist ({n}).",
                                           "fr": "Images de pages enregistrées effacées ({n}).",
                                           "de": "Gespeicherte Seitenbilder gelöscht ({n}).",
                                           "es": "Imágenes de páginas guardadas borradas ({n}).",
                                           "it": "Immagini delle pagine salvate cancellate ({n})."},
    'Choose a PDF, Word or EPUB file': {'nl': 'Kies een pdf-, Word- of EPUB-bestand', 'fr': 'Choisissez un fichier PDF, Word ou EPUB', 'de': 'Wählen Sie eine PDF-, Word- oder EPUB-Datei', 'es': 'Elige un archivo PDF, Word o EPUB', 'it': 'Scegli un file PDF, Word o EPUB'},
    'an EPUB book': {'nl': 'een EPUB-boek', 'fr': 'un livre EPUB', 'de': 'ein EPUB-Buch', 'es': 'un libro EPUB', 'it': 'un libro EPUB'},
    'a Word document': {'nl': 'een Word-document', 'fr': 'un document Word', 'de': 'ein Word-Dokument', 'es': 'un documento de Word', 'it': 'un documento Word'},
    'PDFs (articles, book chapters, scans), Word files and EPUB books all work. Change the layout on the left at any time.': {'nl': "Pdf's (artikels, boekhoofdstukken, scans), Word-bestanden en EPUB-boeken werken allemaal. Pas de opmaak links op elk moment aan.", 'fr': 'Les PDF (articles, chapitres de livres, scans), les fichiers Word et les livres EPUB fonctionnent tous. Modifiez la mise en page à gauche à tout moment.', 'de': 'PDFs (Artikel, Buchkapitel, Scans), Word-Dateien und EPUB-Bücher funktionieren alle. Ändern Sie das Layout links jederzeit.', 'es': 'Los PDF (artículos, capítulos de libros, escaneos), los archivos de Word y los libros EPUB funcionan todos. Cambia el diseño a la izquierda cuando quieras.', 'it': "PDF (articoli, capitoli di libri, scansioni), file Word e libri EPUB funzionano tutti. Cambia l'impaginazione a sinistra quando vuoi."},
    'Reading view': {'nl': 'Leesweergave', 'fr': 'Vue lecture', 'de': 'Leseansicht', 'es': 'Vista de lectura', 'it': 'Vista lettura'},
    'Read the text itself, flowing to fit the window: change the size and spacing at once': {'nl': 'Lees de tekst zelf, passend in het venster: pas grootte en afstand meteen aan', 'fr': "Lisez le texte lui-même, ajusté à la fenêtre : changez la taille et l'espacement aussitôt", 'de': 'Den Text selbst lesen, an das Fenster angepasst: Größe und Abstand sofort ändern', 'es': 'Lee el propio texto, ajustado a la ventana: cambia el tamaño y el espaciado al instante', 'it': "Leggi il testo stesso, adattato alla finestra: cambia dimensione e spaziatura all'istante"},
    'Leave the reading view': {'nl': 'Leesweergave verlaten', 'fr': 'Quitter la vue lecture', 'de': 'Leseansicht verlassen', 'es': 'Salir de la vista de lectura', 'it': 'Esci dalla vista lettura'},
    'Smaller text': {'nl': 'Kleinere tekst', 'fr': 'Texte plus petit', 'de': 'Kleinerer Text', 'es': 'Texto más pequeño', 'it': 'Testo più piccolo'},
    'Larger text': {'nl': 'Grotere tekst', 'fr': 'Texte plus grand', 'de': 'Größerer Text', 'es': 'Texto más grande', 'it': 'Testo più grande'},
    'More space between lines': {'nl': 'Meer ruimte tussen de regels', 'fr': "Plus d'espace entre les lignes", 'de': 'Mehr Abstand zwischen den Zeilen', 'es': 'Más espacio entre líneas', 'it': 'Più spazio tra le righe'},
    'Less space between lines': {'nl': 'Minder ruimte tussen de regels', 'fr': "Moins d'espace entre les lignes", 'de': 'Weniger Abstand zwischen den Zeilen', 'es': 'Menos espacio entre líneas', 'it': 'Meno spazio tra le righe'},
    'Column width': {'nl': 'Kolombreedte', 'fr': 'Largeur de colonne', 'de': 'Spaltenbreite', 'es': 'Ancho de columna', 'it': 'Larghezza della colonna'},
    'Show the pages (focus mode)': {'nl': "Toon de pagina's (focusmodus)", 'fr': 'Afficher les pages (mode concentration)', 'de': 'Seiten zeigen (Fokusmodus)', 'es': 'Mostrar las páginas (modo concentración)', 'it': 'Mostra le pagine (modalità concentrazione)'},
    'Study sheet': {'nl': 'Studieblad', 'fr': "Fiche d'étude", 'de': 'Lernblatt', 'es': 'Hoja de estudio', 'it': 'Scheda di studio'},
    'Your highlights and notes gathered under the headings they are in, as a Word document to study from': {'nl': 'Je markeringen en notities, gegroepeerd onder hun titels, als Word-document om mee te studeren', 'fr': 'Vos surlignages et notes regroupés sous leurs titres, en document Word pour étudier', 'de': 'Ihre Markierungen und Notizen, unter ihren Überschriften gesammelt, als Word-Dokument zum Lernen', 'es': 'Tus resaltados y notas agrupados bajo sus títulos, en un documento de Word para estudiar', 'it': 'Le tue evidenziazioni e note raccolte sotto i loro titoli, in un documento Word per studiare'},
    '{highlights} highlights, {notes} with a note': {'nl': '{highlights} markeringen, {notes} met een notitie', 'fr': '{highlights} surlignages, dont {notes} avec une note', 'de': '{highlights} Markierungen, {notes} mit Notiz', 'es': '{highlights} resaltados, {notes} con una nota', 'it': '{highlights} evidenziazioni, {notes} con una nota'},
    '(page {page})': {'nl': '(pagina {page})', 'fr': '(page {page})', 'de': '(Seite {page})', 'es': '(página {page})', 'it': '(pagina {page})'},
    'Before the first heading': {'nl': 'Voor de eerste titel', 'fr': 'Avant le premier titre', 'de': 'Vor der ersten Überschrift', 'es': 'Antes del primer título', 'it': 'Prima del primo titolo'},
    'Study sheet: {name}': {'nl': 'Studieblad: {name}', 'fr': "Fiche d'étude : {name}", 'de': 'Lernblatt: {name}', 'es': 'Hoja de estudio: {name}', 'it': 'Scheda di studio: {name}'},
    'Explanation': {'nl': 'Uitleg', 'fr': 'Explication', 'de': 'Erklärung', 'es': 'Explicación', 'it': 'Spiegazione'},
    'AI explanation': {'nl': 'AI-uitleg', 'fr': "Explication par l'IA", 'de': 'KI-Erklärung', 'es': 'Explicación de la IA', 'it': "Spiegazione dell'IA"},
    'Explain': {'nl': 'Uitleggen', 'fr': 'Expliquer', 'de': 'Erklären', 'es': 'Explicar', 'it': 'Spiega'},
    'Explain what a hard part means, in plain words, with its difficult words': {'nl': 'Leg in eenvoudige woorden uit wat een moeilijk stuk betekent, met de moeilijke woorden', 'fr': 'Expliquer en mots simples ce que veut dire un passage difficile, avec ses mots difficiles', 'de': 'Erklären, was eine schwierige Stelle bedeutet, in einfachen Worten, mit ihren schwierigen Wörtern', 'es': 'Explicar con palabras sencillas lo que significa una parte difícil, con sus palabras difíciles', 'it': 'Spiegare con parole semplici cosa significa una parte difficile, con le sue parole difficili'},
    'Only the first {n} words are explained. Select a shorter part to explain all of it.': {'nl': 'Alleen de eerste {n} woorden worden uitgelegd. Selecteer een korter stuk om alles uit te leggen.', 'fr': 'Seuls les {n} premiers mots sont expliqués. Sélectionnez un passage plus court pour tout expliquer.', 'de': 'Nur die ersten {n} Wörter werden erklärt. Wählen Sie eine kürzere Stelle, um alles zu erklären.', 'es': 'Solo se explican las primeras {n} palabras. Selecciona una parte más corta para explicarla entera.', 'it': 'Vengono spiegate solo le prime {n} parole. Seleziona una parte più breve per spiegarla tutta.'},
    'Explaining...': {'nl': 'Bezig met uitleggen...', 'fr': 'Explication en cours...', 'de': 'Wird erklärt...', 'es': 'Explicando...', 'it': 'Spiegazione in corso...'},
    'AI explanation (check it against the text):': {'nl': 'AI-uitleg (controleer die met de tekst):', 'fr': "Explication par l'IA (à vérifier avec le texte) :", 'de': 'KI-Erklärung (mit dem Text vergleichen):', 'es': 'Explicación de la IA (compárala con el texto):', 'it': "Spiegazione dell'IA (confrontala con il testo):"},
    'AI explains what the selection means, in plain words': {'nl': 'AI legt in eenvoudige woorden uit wat de selectie betekent', 'fr': "L'IA explique en mots simples ce que veut dire la sélection", 'de': 'Die KI erklärt in einfachen Worten, was die Auswahl bedeutet', 'es': 'La IA explica con palabras sencillas lo que significa la selección', 'it': "L'IA spiega con parole semplici cosa significa la selezione"},
    'Note:': {'nl': 'Notitie:', 'fr': 'Note :', 'de': 'Notiz:', 'es': 'Nota:', 'it': 'Nota:'},
    'AI can make mistakes. Check the explanation against the text before you use it.': {'nl': 'AI kan fouten maken. Controleer de uitleg met de tekst voor je hem gebruikt.', 'fr': "L'IA peut se tromper. Vérifiez l'explication avec le texte avant de l'utiliser.", 'de': 'KI kann Fehler machen. Vergleichen Sie die Erklärung mit dem Text, bevor Sie sie verwenden.', 'es': 'La IA puede equivocarse. Compara la explicación con el texto antes de usarla.', 'it': "L'IA può sbagliare. Confronta la spiegazione con il testo prima di usarla."},
    'Version {version} is available (you have {current}). Download it from the project page.': {'nl': 'Versie {version} is beschikbaar (je hebt {current}). Download ze via de projectpagina.', 'fr': 'La version {version} est disponible (vous avez la {current}). Téléchargez-la sur la page du projet.', 'de': 'Version {version} ist verfügbar (Sie haben {current}). Laden Sie sie auf der Projektseite herunter.', 'es': 'La versión {version} está disponible (tienes la {current}). Descárgala en la página del proyecto.', 'it': 'La versione {version} è disponibile (hai la {current}). Scaricala dalla pagina del progetto.'},
    'Download': {'nl': 'Downloaden', 'fr': 'Télécharger', 'de': 'Herunterladen', 'es': 'Descargar', 'it': 'Scarica'},
    'Tell me when a new version is out': {'nl': 'Laat me weten wanneer er een nieuwe versie is', 'fr': 'Me prévenir quand une nouvelle version sort', 'de': 'Mich informieren, wenn eine neue Version erscheint', 'es': 'Avisarme cuando salga una nueva versión', 'it': 'Avvisami quando esce una nuova versione'},
    'The app asks GitHub once a day which version is the newest. Nothing about you or your documents is sent.': {'nl': 'De app vraagt GitHub één keer per dag welke versie de nieuwste is. Er wordt niets over jou of je documenten verstuurd.', 'fr': "L'application demande une fois par jour à GitHub quelle est la version la plus récente. Rien sur vous ni sur vos documents n'est envoyé.", 'de': 'Die App fragt GitHub einmal am Tag, welche Version die neueste ist. Nichts über Sie oder Ihre Dokumente wird gesendet.', 'es': 'La aplicación pregunta a GitHub una vez al día cuál es la versión más reciente. No se envía nada sobre ti ni tus documentos.', 'it': "L'app chiede a GitHub una volta al giorno qual è la versione più recente. Non viene inviato nulla su di te o sui tuoi documenti."},
    'Open file': {'nl': 'Bestand openen', 'fr': 'Ouvrir un fichier', 'de': 'Datei öffnen', 'es': 'Abrir archivo', 'it': 'Apri file'},
    'Open a document to start': {'nl': 'Open een document om te beginnen', 'fr': 'Ouvrez un document pour commencer', 'de': 'Öffnen Sie ein Dokument, um zu beginnen', 'es': 'Abre un documento para empezar', 'it': 'Apri un documento per iniziare'},
    'This Word file is protected with a password. Open it in Word, remove the password (File > Info > Protect Document), save it, and open it here again.': {'nl': 'Dit Word-bestand is beveiligd met een wachtwoord. Open het in Word, verwijder het wachtwoord (Bestand > Info > Document beveiligen), sla het op en open het hier opnieuw.', 'fr': 'Ce fichier Word est protégé par un mot de passe. Ouvrez-le dans Word, supprimez le mot de passe (Fichier > Informations > Protéger le document), enregistrez-le et ouvrez-le ici à nouveau.', 'de': 'Diese Word-Datei ist mit einem Kennwort geschützt. Öffnen Sie sie in Word, entfernen Sie das Kennwort (Datei > Informationen > Dokument schützen), speichern Sie sie und öffnen Sie sie hier erneut.', 'es': 'Este archivo de Word está protegido con contraseña. Ábrelo en Word, quita la contraseña (Archivo > Información > Proteger documento), guárdalo y vuelve a abrirlo aquí.', 'it': 'Questo file Word è protetto da password. Aprilo in Word, rimuovi la password (File > Informazioni > Proteggi documento), salvalo e aprilo di nuovo qui.'},
    "This e-book is copy-protected (DRM) by the shop it came from, so only that shop's reading app can open it. The converter cannot read protected books. Books without DRM work: many shops sell them, and libraries such as Project Gutenberg and Standard Ebooks are free.": {'nl': 'Dit e-boek is kopieerbeveiligd (DRM) door de winkel waar het vandaan komt, dus alleen de lees-app van die winkel kan het openen. De converter kan beveiligde boeken niet lezen. Boeken zonder DRM werken wel: veel winkels verkopen ze, en bibliotheken zoals Project Gutenberg en Standard Ebooks zijn gratis.', 'fr': "Ce livre numérique est protégé contre la copie (DRM) par la boutique d'où il vient : seule l'application de lecture de cette boutique peut l'ouvrir. Le convertisseur ne peut pas lire les livres protégés. Les livres sans DRM fonctionnent : beaucoup de boutiques en vendent, et des bibliothèques comme Project Gutenberg et Standard Ebooks sont gratuites.", 'de': 'Dieses E-Book ist vom Shop, aus dem es stammt, kopiergeschützt (DRM), daher kann nur die Lese-App dieses Shops es öffnen. Der Konverter kann geschützte Bücher nicht lesen. Bücher ohne DRM funktionieren: Viele Shops verkaufen sie, und Bibliotheken wie Project Gutenberg und Standard Ebooks sind kostenlos.', 'es': 'Este libro electrónico está protegido contra copia (DRM) por la tienda de la que procede, así que solo la aplicación de lectura de esa tienda puede abrirlo. El conversor no puede leer libros protegidos. Los libros sin DRM funcionan: muchas tiendas los venden, y bibliotecas como Project Gutenberg y Standard Ebooks son gratuitas.', 'it': "Questo e-book è protetto da copia (DRM) dal negozio da cui proviene, quindi solo l'app di lettura di quel negozio può aprirlo. Il convertitore non può leggere libri protetti. I libri senza DRM funzionano: molti negozi li vendono, e biblioteche come Project Gutenberg e Standard Ebooks sono gratuite."},
    'Could not read this file:': {'nl': 'Kon dit bestand niet lezen:', 'fr': 'Impossible de lire ce fichier :', 'de': 'Diese Datei konnte nicht gelesen werden:', 'es': 'No se pudo leer este archivo:', 'it': 'Impossibile leggere questo file:'},
    'Drop the file to open it': {'nl': 'Laat het bestand los om het te openen', 'fr': "Déposez le fichier pour l'ouvrir", 'de': 'Datei loslassen, um sie zu öffnen', 'es': 'Suelta el archivo para abrirlo', 'it': 'Rilascia il file per aprirlo'},
    'PDF, Word (.docx) or EPUB': {'nl': 'Pdf, Word (.docx) of EPUB', 'fr': 'PDF, Word (.docx) ou EPUB', 'de': 'PDF, Word (.docx) oder EPUB', 'es': 'PDF, Word (.docx) o EPUB', 'it': 'PDF, Word (.docx) o EPUB'},
    'Drop a PDF, Word (.docx) or EPUB file to open it.': {'nl': 'Sleep een pdf-, Word- (.docx) of EPUB-bestand hierheen om het te openen.', 'fr': "Déposez un fichier PDF, Word (.docx) ou EPUB pour l'ouvrir.", 'de': 'Ziehen Sie eine PDF-, Word- (.docx) oder EPUB-Datei hierher, um sie zu öffnen.', 'es': 'Suelta un archivo PDF, Word (.docx) o EPUB para abrirlo.', 'it': 'Trascina qui un file PDF, Word (.docx) o EPUB per aprirlo.'},
    'Or drop a file anywhere in this window.': {'nl': 'Of sleep een bestand ergens in dit venster.', 'fr': "Ou déposez un fichier n'importe où dans cette fenêtre.", 'de': 'Oder ziehen Sie eine Datei an eine beliebige Stelle in diesem Fenster.', 'es': 'O suelta un archivo en cualquier parte de esta ventana.', 'it': 'Oppure trascina un file in un punto qualsiasi di questa finestra.'},
    'Web page': {'nl': 'Webpagina', 'fr': 'Page web', 'de': 'Webseite', 'es': 'Página web', 'it': 'Pagina web'},
    'Open an article from a web page': {'nl': 'Een artikel van een webpagina openen', 'fr': "Ouvrir un article d'une page web", 'de': 'Einen Artikel von einer Webseite öffnen', 'es': 'Abrir un artículo de una página web', 'it': 'Apri un articolo da una pagina web'},
    'PDFs (articles, book chapters, scans), Word files, EPUB books and web articles all work. Change the layout on the left at any time.': {'nl': "Pdf's (artikelen, hoofdstukken, scans), Word-bestanden, EPUB-boeken en webartikelen werken allemaal. Pas de opmaak links op elk moment aan.", 'fr': 'Les PDF (articles, chapitres, scans), les fichiers Word, les livres EPUB et les articles web fonctionnent tous. Modifiez la mise en page à gauche à tout moment.', 'de': 'PDFs (Artikel, Buchkapitel, Scans), Word-Dateien, EPUB-Bücher und Webartikel funktionieren alle. Ändern Sie das Layout links jederzeit.', 'es': 'Funcionan los PDF (artículos, capítulos, escaneos), los archivos de Word, los libros EPUB y los artículos web. Cambia el diseño a la izquierda cuando quieras.', 'it': 'Funzionano i PDF (articoli, capitoli, scansioni), i file Word, i libri EPUB e gli articoli web. Cambia il layout a sinistra in qualsiasi momento.'},
    'Address of the page': {'nl': 'Adres van de pagina', 'fr': 'Adresse de la page', 'de': 'Adresse der Seite', 'es': 'Dirección de la página', 'it': 'Indirizzo della pagina'},
    'Open a web page': {'nl': 'Een webpagina openen', 'fr': 'Ouvrir une page web', 'de': 'Eine Webseite öffnen', 'es': 'Abrir una página web', 'it': 'Apri una pagina web'},
    'Paste the address of an article. Only the article is kept: menus, adverts and comments are left out. Pages behind a login or paywall cannot be opened.': {'nl': "Plak het adres van een artikel. Alleen het artikel wordt bewaard: menu's, advertenties en reacties worden weggelaten. Pagina's achter een login of betaalmuur kunnen niet worden geopend.", 'fr': "Collez l'adresse d'un article. Seul l'article est conservé : les menus, publicités et commentaires sont omis. Les pages derrière une connexion ou un paywall ne peuvent pas être ouvertes.", 'de': 'Fügen Sie die Adresse eines Artikels ein. Nur der Artikel wird behalten: Menüs, Werbung und Kommentare werden weggelassen. Seiten hinter einer Anmeldung oder Bezahlschranke können nicht geöffnet werden.', 'es': 'Pega la dirección de un artículo. Solo se conserva el artículo: se omiten los menús, anuncios y comentarios. Las páginas que requieren inicio de sesión o suscripción no se pueden abrir.', 'it': "Incolla l'indirizzo di un articolo. Viene conservato solo l'articolo: menu, pubblicità e commenti vengono omessi. Le pagine dietro un login o un paywall non possono essere aperte."},
    'Open': {'nl': 'Openen', 'fr': 'Ouvrir', 'de': 'Öffnen', 'es': 'Abrir', 'it': 'Apri'},
    'Downloading the web page...': {'nl': 'De webpagina wordt gedownload...', 'fr': 'Téléchargement de la page web...', 'de': 'Die Webseite wird heruntergeladen...', 'es': 'Descargando la página web...', 'it': 'Download della pagina web...'},
    'Could not open the web page.': {'nl': 'De webpagina kon niet worden geopend.', 'fr': "Impossible d'ouvrir la page web.", 'de': 'Die Webseite konnte nicht geöffnet werden.', 'es': 'No se pudo abrir la página web.', 'it': 'Impossibile aprire la pagina web.'},
    'a web page': {'nl': 'een webpagina', 'fr': 'une page web', 'de': 'eine Webseite', 'es': 'una página web', 'it': 'una pagina web'},
    'Type the address of a web page': {'nl': 'Typ het adres van een webpagina', 'fr': "Tapez l'adresse d'une page web", 'de': 'Geben Sie die Adresse einer Webseite ein', 'es': 'Escribe la dirección de una página web', 'it': "Digita l'indirizzo di una pagina web"},
    'This is not the address of a web page': {'nl': 'Dit is geen adres van een webpagina', 'fr': "Ce n'est pas l'adresse d'une page web", 'de': 'Das ist keine Adresse einer Webseite', 'es': 'Esta no es la dirección de una página web', 'it': "Questo non è l'indirizzo di una pagina web"},
    'The page could not be downloaded. Check the address and the internet connection.': {'nl': 'De pagina kon niet worden gedownload. Controleer het adres en de internetverbinding.', 'fr': "La page n'a pas pu être téléchargée. Vérifiez l'adresse et la connexion internet.", 'de': 'Die Seite konnte nicht heruntergeladen werden. Prüfen Sie die Adresse und die Internetverbindung.', 'es': 'No se pudo descargar la página. Comprueba la dirección y la conexión a internet.', 'it': "Impossibile scaricare la pagina. Controlla l'indirizzo e la connessione internet."},
    'The site did not give the page (it may not exist, or it needs a login).': {'nl': 'De site gaf de pagina niet (ze bestaat misschien niet, of vraagt een login).', 'fr': "Le site n'a pas fourni la page (elle n'existe peut-être pas ou nécessite une connexion).", 'de': 'Die Website hat die Seite nicht geliefert (sie existiert vielleicht nicht oder erfordert eine Anmeldung).', 'es': 'El sitio no entregó la página (puede que no exista o que requiera iniciar sesión).', 'it': 'Il sito non ha fornito la pagina (potrebbe non esistere o richiedere un login).'},
    'This address is a file, not a web page. Download it and open it with Open file.': {'nl': 'Dit adres is een bestand, geen webpagina. Download het en open het met Bestand openen.', 'fr': 'Cette adresse est un fichier, pas une page web. Téléchargez-le et ouvrez-le avec Ouvrir un fichier.', 'de': 'Diese Adresse ist eine Datei, keine Webseite. Laden Sie sie herunter und öffnen Sie sie mit Datei öffnen.', 'es': 'Esta dirección es un archivo, no una página web. Descárgalo y ábrelo con Abrir archivo.', 'it': 'Questo indirizzo è un file, non una pagina web. Scaricalo e aprilo con Apri file.'},
    'The page could not be read': {'nl': 'De pagina kon niet worden gelezen', 'fr': "La page n'a pas pu être lue", 'de': 'Die Seite konnte nicht gelesen werden', 'es': 'No se pudo leer la página', 'it': 'Impossibile leggere la pagina'},
    'No article text was found on this page': {'nl': 'Er is geen artikeltekst gevonden op deze pagina', 'fr': "Aucun texte d'article n'a été trouvé sur cette page", 'de': 'Auf dieser Seite wurde kein Artikeltext gefunden', 'es': 'No se encontró texto de artículo en esta página', 'it': 'Nessun testo di articolo trovato in questa pagina'},
    'No colour help': {'nl': 'Geen kleurhulp', 'fr': 'Sans aide couleur', 'de': 'Keine Farbhilfe', 'es': 'Sin ayuda de color', 'it': 'Nessun aiuto colore'},
    'Colour syllables': {'nl': 'Lettergrepen kleuren', 'fr': 'Colorer les syllabes', 'de': 'Silben einfärben', 'es': 'Colorear sílabas', 'it': 'Colora le sillabe'},
    'Colour sentences': {'nl': 'Zinnen kleuren', 'fr': 'Colorer les phrases', 'de': 'Sätze einfärben', 'es': 'Colorear frases', 'it': 'Colora le frasi'},
    'Colour help: syllables or sentences in two colours': {'nl': 'Kleurhulp: lettergrepen of zinnen in twee kleuren', 'fr': 'Aide couleur : syllabes ou phrases en deux couleurs', 'de': 'Farbhilfe: Silben oder Sätze in zwei Farben', 'es': 'Ayuda de color: sílabas o frases en dos colores', 'it': 'Aiuto colore: sillabe o frasi in due colori'},
    'Reading speed (kept for this document)': {'nl': 'Leessnelheid (bewaard voor dit document)', 'fr': 'Vitesse de lecture (gardée pour ce document)', 'de': 'Lesegeschwindigkeit (für dieses Dokument gespeichert)', 'es': 'Velocidad de lectura (guardada para este documento)', 'it': 'Velocità di lettura (salvata per questo documento)'},
    'Read along': {'nl': 'Meelezen', 'fr': 'Lecture suivie', 'de': 'Mitlesen', 'es': 'Leer a la vez', 'it': 'Leggi insieme'},
    'Read the text itself, flowing to fit the window, with the sentence and word being read marked; size, spacing and colours change at once': {'nl': 'Lees de tekst zelf, passend in het venster, met de zin en het woord dat wordt voorgelezen gemarkeerd; grootte, ruimte en kleuren veranderen meteen', 'fr': 'Lire le texte lui-même, adapté à la fenêtre, avec la phrase et le mot lus mis en évidence ; taille, espacement et couleurs changent aussitôt', 'de': 'Den Text selbst lesen, ans Fenster angepasst, mit markiertem Satz und Wort, die gerade vorgelesen werden; Größe, Abstände und Farben ändern sich sofort', 'es': 'Leer el texto en sí, ajustado a la ventana, con la frase y la palabra que se leen marcadas; tamaño, espaciado y colores cambian al instante', 'it': 'Leggi il testo stesso, adattato alla finestra, con la frase e la parola lette evidenziate; dimensione, spaziatura e colori cambiano subito'},
    'Leave read along': {'nl': 'Meelezen verlaten', 'fr': 'Quitter la lecture suivie', 'de': 'Mitlesen verlassen', 'es': 'Salir de leer a la vez', 'it': 'Esci da leggi insieme'},
    'Selection': {'nl': 'Selectie', 'fr': 'Sélection', 'de': 'Auswahl', 'es': 'Selección', 'it': 'Selezione'},
    'Select the sentence or paragraph, or move the start or end': {'nl': 'Selecteer de zin of alinea, of verschuif het begin of einde', 'fr': 'Sélectionner la phrase ou le paragraphe, ou déplacer le début ou la fin', 'de': 'Satz oder Absatz auswählen oder Anfang oder Ende verschieben', 'es': 'Seleccionar la frase o el párrafo, o mover el inicio o el final', 'it': "Seleziona la frase o il paragrafo, o sposta l'inizio o la fine"},
    'Start one word earlier': {'nl': 'Begin een woord eerder', 'fr': 'Début un mot plus tôt', 'de': 'Anfang ein Wort früher', 'es': 'Inicio una palabra antes', 'it': 'Inizio una parola prima'},
    'Start one word later': {'nl': 'Begin een woord later', 'fr': 'Début un mot plus tard', 'de': 'Anfang ein Wort später', 'es': 'Inicio una palabra después', 'it': 'Inizio una parola dopo'},
    'End one word earlier': {'nl': 'Einde een woord eerder', 'fr': 'Fin un mot plus tôt', 'de': 'Ende ein Wort früher', 'es': 'Final una palabra antes', 'it': 'Fine una parola prima'},
    'End one word later': {'nl': 'Einde een woord later', 'fr': 'Fin un mot plus tard', 'de': 'Ende ein Wort später', 'es': 'Final una palabra después', 'it': 'Fine una parola dopo'},
    "Correct these words (for example a word split by a space)": {
        "nl": "Deze woorden verbeteren (bijvoorbeeld een woord dat door een spatie is gesplitst)",
        "fr": "Corriger ces mots (par exemple un mot coupé par une espace)",
        "de": "Diese Wörter korrigieren (zum Beispiel ein durch ein Leerzeichen getrenntes Wort)",
        "es": "Corregir estas palabras (por ejemplo, una palabra separada por un espacio)",
        "it": "Correggi queste parole (ad esempio una parola divisa da uno spazio)"},
    "These words can't be edited: the converter added or moved them (for example reference numbers). Select words of the text itself.": {
        "nl": "Deze woorden kunnen niet bewerkt worden: de converter heeft ze toegevoegd of verplaatst (bijvoorbeeld "
              "verwijzingsnummers). Selecteer woorden uit de tekst zelf.",
        "fr": "Ces mots ne peuvent pas être modifiés : le convertisseur les a ajoutés ou déplacés (par exemple des "
              "numéros de référence). Sélectionnez des mots du texte lui-même.",
        "de": "Diese Wörter können nicht bearbeitet werden: Der Konverter hat sie hinzugefügt oder verschoben (zum "
              "Beispiel Verweisnummern). Wählen Sie Wörter aus dem Text selbst.",
        "es": "Estas palabras no se pueden editar: el conversor las añadió o las movió (por ejemplo, números de "
              "referencia). Seleccione palabras del propio texto.",
        "it": "Queste parole non si possono modificare: il convertitore le ha aggiunte o spostate (ad esempio i "
              "numeri dei riferimenti). Seleziona parole del testo stesso."},
    "Type the words as they should read. The original document is not changed and you can undo this.": {
        "nl": "Typ de woorden zoals ze moeten zijn. Het originele document verandert niet en u kunt dit ongedaan maken.",
        "fr": "Tapez les mots tels qu'ils doivent être. Le document original n'est pas modifié et vous pouvez annuler.",
        "de": "Geben Sie die Wörter so ein, wie sie lauten sollen. Das Originaldokument wird nicht geändert und Sie "
              "können dies rückgängig machen.",
        "es": "Escriba las palabras como deben quedar. El documento original no cambia y puede deshacerlo.",
        "it": "Scrivi le parole come devono essere. Il documento originale non cambia e puoi annullare."},
    "Your correction was saved.": {"nl": "Uw verbetering is bewaard.", "fr": "Votre correction a été enregistrée.",
                                   "de": "Ihre Korrektur wurde gespeichert.", "es": "Se guardó su corrección.",
                                   "it": "La tua correzione è stata salvata."},
    "Words that may be split by a space": {"nl": "Woorden die door een spatie gesplitst kunnen zijn",
                                           "fr": "Mots peut-être coupés par une espace",
                                           "de": "Wörter, die durch ein Leerzeichen getrennt sein können",
                                           "es": "Palabras que quizá estén separadas por un espacio",
                                           "it": "Parole forse divise da uno spazio"},
    "Natural voices": {"nl": "Natuurlijke stemmen", "fr": "Voix naturelles", "de": "Natürliche Stimmen",
                       "es": "Voces naturales", "it": "Voci naturali"},
    "Download natural-sounding voices that work offline": {
        "nl": "Natuurlijk klinkende stemmen downloaden die offline werken",
        "fr": "Télécharger des voix au son naturel qui fonctionnent hors ligne",
        "de": "Natürlich klingende Stimmen herunterladen, die offline funktionieren",
        "es": "Descargar voces de sonido natural que funcionan sin conexión",
        "it": "Scarica voci dal suono naturale che funzionano offline"},
    "Downloaded": {"nl": "Gedownload", "fr": "Téléchargée", "de": "Heruntergeladen", "es": "Descargada",
                   "it": "Scaricata"},
    "man": {"nl": "man", "fr": "homme", "de": "Mann", "es": "hombre", "it": "uomo"},
    "woman": {"nl": "vrouw", "fr": "femme", "de": "Frau", "es": "mujer", "it": "donna"},
    "The voice could not be downloaded:": {"nl": "De stem kon niet gedownload worden:",
                                           "fr": "La voix n'a pas pu être téléchargée :",
                                           "de": "Die Stimme konnte nicht heruntergeladen werden:",
                                           "es": "No se pudo descargar la voz:",
                                           "it": "Non è stato possibile scaricare la voce:"},
    "The natural voice {name} is ready. With the voice on Automatic it reads {language} documents.": {
        "nl": "De natuurlijke stem {name} is klaar. Met de stem op Automatisch leest ze {language} documenten voor.",
        "fr": "La voix naturelle {name} est prête. Avec la voix sur Automatique, elle lit les documents en {language}.",
        "de": "Die natürliche Stimme {name} ist bereit. Mit der Stimme auf Automatisch liest sie Dokumente auf "
              "{language} vor.",
        "es": "La voz natural {name} está lista. Con la voz en Automática, lee los documentos en {language}.",
        "it": "La voce naturale {name} è pronta. Con la voce su Automatica legge i documenti in {language}."},
    "No {language} voice is installed, so another voice reads the text. Download a natural {language} voice with Natural voices in the read-aloud panel.": {
        "nl": "Er is geen stem voor {language} geïnstalleerd, dus een andere stem leest de tekst voor. Download een "
              "natuurlijke stem voor {language} met Natuurlijke stemmen in het voorleespaneel.",
        "fr": "Aucune voix {language} n'est installée, une autre voix lit donc le texte. Téléchargez une voix "
              "naturelle {language} avec Voix naturelles dans le panneau de lecture.",
        "de": "Es ist keine Stimme für {language} installiert, daher liest eine andere Stimme den Text. Laden Sie "
              "mit Natürliche Stimmen im Vorlesebereich eine natürliche Stimme für {language} herunter.",
        "es": "No hay ninguna voz en {language} instalada, así que otra voz lee el texto. Descargue una voz "
              "natural en {language} con Voces naturales en el panel de lectura.",
        "it": "Non è installata nessuna voce in {language}, quindi un'altra voce legge il testo. Scarica una voce "
              "naturale in {language} con Voci naturali nel pannello di lettura."},
    "These voices sound much more natural than most voices built into the computer. Each is downloaded once (about 60 MB) and then works offline: the text you read never leaves this device.": {
        "nl": "Deze stemmen klinken veel natuurlijker dan de meeste stemmen van de computer. Elke stem wordt één "
              "keer gedownload (ongeveer 60 MB) en werkt daarna offline: de tekst die u leest verlaat dit apparaat "
              "nooit.",
        "fr": "Ces voix sont bien plus naturelles que la plupart des voix de l'ordinateur. Chacune est téléchargée "
              "une fois (environ 60 Mo) puis fonctionne hors ligne : le texte que vous lisez ne quitte jamais cet "
              "appareil.",
        "de": "Diese Stimmen klingen viel natürlicher als die meisten Stimmen des Computers. Jede wird einmal "
              "heruntergeladen (etwa 60 MB) und funktioniert dann offline: Der Text, den Sie lesen, verlässt "
              "dieses Gerät nie.",
        "es": "Estas voces suenan mucho más naturales que la mayoría de las voces del ordenador. Cada una se "
              "descarga una vez (unos 60 MB) y luego funciona sin conexión: el texto que lee nunca sale de este "
              "dispositivo.",
        "it": "Queste voci suonano molto più naturali della maggior parte delle voci del computer. Ognuna si "
              "scarica una volta (circa 60 MB) e poi funziona offline: il testo che leggi non lascia mai questo "
              "dispositivo."},
    "Reference": {"nl": "Bron", "fr": "Référence", "de": "Quelle", "es": "Referencia", "it": "Riferimento"},
    "References": {"nl": "Bronnen", "fr": "Références", "de": "Quellen", "es": "Referencias", "it": "Riferimenti"},
    "Show in the list": {"nl": "Tonen in de lijst", "fr": "Afficher dans la liste", "de": "In der Liste zeigen",
                         "es": "Mostrar en la lista", "it": "Mostra nell'elenco"},
    "Save as audio": {"nl": "Opslaan als audio", "fr": "Enregistrer en audio", "de": "Als Audio speichern",
                      "es": "Guardar como audio", "it": "Salva come audio"},
    "Save as audio (MP3): the whole document, some pages or your selection": {
        "nl": "Opslaan als audio (MP3): het hele document, een paar pagina's of uw selectie",
        "fr": "Enregistrer en audio (MP3) : tout le document, quelques pages ou votre sélection",
        "de": "Als Audio speichern (MP3): das ganze Dokument, einige Seiten oder Ihre Auswahl",
        "es": "Guardar como audio (MP3): todo el documento, algunas páginas o su selección",
        "it": "Salva come audio (MP3): tutto il documento, alcune pagine o la tua selezione"},
    "Save MP3": {"nl": "MP3 opslaan", "fr": "Enregistrer le MP3", "de": "MP3 speichern", "es": "Guardar MP3",
                 "it": "Salva MP3"},
    "Whole document": {"nl": "Hele document", "fr": "Tout le document", "de": "Ganzes Dokument",
                       "es": "Todo el documento", "it": "Tutto il documento"},
    "Pages": {"nl": "Pagina's", "fr": "Pages", "de": "Seiten", "es": "Páginas", "it": "Pagine"},
    "to": {"nl": "tot", "fr": "à", "de": "bis", "es": "a", "it": "a"},
    "about {n} minutes": {"nl": "ongeveer {n} minuten", "fr": "environ {n} minutes", "de": "etwa {n} Minuten",
                          "es": "unos {n} minutos", "it": "circa {n} minuti"},
    "under a minute": {"nl": "minder dan een minuut", "fr": "moins d'une minute", "de": "unter einer Minute",
                       "es": "menos de un minuto", "it": "meno di un minuto"},
    "Making the audio...": {"nl": "De audio wordt gemaakt...", "fr": "Création de l'audio...",
                            "de": "Audio wird erstellt...", "es": "Creando el audio...", "it": "Creazione dell'audio..."},
    "The audio could not be made:": {"nl": "De audio kon niet gemaakt worden:", "fr": "L'audio n'a pas pu être créé :",
                                     "de": "Das Audio konnte nicht erstellt werden:",
                                     "es": "No se pudo crear el audio:", "it": "Non è stato possibile creare l'audio:"},
    "MP3": {"nl": "MP3", "fr": "MP3", "de": "MP3", "es": "MP3", "it": "MP3"},
    "MP3 (text to speech)": {"nl": "MP3 (tekst naar spraak)", "fr": "MP3 (synthèse vocale)",
                             "de": "MP3 (Sprachausgabe)", "es": "MP3 (texto a voz)", "it": "MP3 (sintesi vocale)"},
    "What to read": {"nl": "Wat voorlezen", "fr": "Que lire", "de": "Was vorlesen", "es": "Qué leer",
                     "it": "Cosa leggere"},
    "Leave out": {"nl": "Weglaten", "fr": "Laisser de côté", "de": "Weglassen", "es": "Omitir", "it": "Tralascia"},
    "Natural (Piper)": {"nl": "Natuurlijk (Piper)", "fr": "Naturelles (Piper)", "de": "Natürlich (Piper)",
                        "es": "Naturales (Piper)", "it": "Naturali (Piper)"},
    "Windows voices": {"nl": "Windows-stemmen", "fr": "Voix Windows", "de": "Windows-Stimmen", "es": "Voces de Windows",
                       "it": "Voci di Windows"},
    "Computer voices": {"nl": "Computerstemmen", "fr": "Voix de l'ordinateur", "de": "Computerstimmen",
                        "es": "Voces del ordenador", "it": "Voci del computer"},
    "Download natural voices": {"nl": "Natuurlijke stemmen downloaden", "fr": "Télécharger des voix naturelles",
                                "de": "Natürliche Stimmen herunterladen", "es": "Descargar voces naturales",
                                "it": "Scarica voci naturali"},
    "Skip citations in the text, like (Smith, 2019) and [3]": {
        "nl": "Verwijzingen in de tekst overslaan, zoals (Smith, 2019) en [3]",
        "fr": "Ignorer les citations dans le texte, comme (Smith, 2019) et [3]",
        "de": "Zitate im Text überspringen, wie (Smith, 2019) und [3]",
        "es": "Omitir las citas en el texto, como (Smith, 2019) y [3]",
        "it": "Salta le citazioni nel testo, come (Smith, 2019) e [3]"},
    "Most are found, but some unusual ones may still be read.": {
        "nl": "De meeste worden gevonden, maar sommige ongewone kunnen toch voorgelezen worden.",
        "fr": "La plupart sont trouvées, mais certaines inhabituelles peuvent encore être lues.",
        "de": "Die meisten werden gefunden, aber einige ungewöhnliche werden vielleicht doch vorgelesen.",
        "es": "Se encuentran casi todas, pero algunas poco habituales pueden leerse igualmente.",
        "it": "Quasi tutte vengono trovate, ma alcune insolite potrebbero essere lette comunque."},
    "Skip the reference list and notes at the end": {
        "nl": "De literatuurlijst en noten aan het eind overslaan",
        "fr": "Ignorer la bibliographie et les notes à la fin",
        "de": "Literaturverzeichnis und Anmerkungen am Ende überspringen",
        "es": "Omitir la lista de referencias y las notas del final",
        "it": "Salta la bibliografia e le note alla fine"},
    "No reference list or notes were found": {"nl": "Er is geen literatuurlijst of noten gevonden",
                                              "fr": "Aucune bibliographie ni note n'a été trouvée",
                                              "de": "Kein Literaturverzeichnis und keine Anmerkungen gefunden",
                                              "es": "No se encontraron referencias ni notas",
                                              "it": "Nessuna bibliografia o nota trovata"},
    "Saving MP3 files needs the lameenc package (pip install lameenc); the app download includes it.": {
        "nl": "Voor MP3-bestanden is het pakket lameenc nodig (pip install lameenc); de app-download bevat het.",
        "fr": "L'enregistrement en MP3 nécessite le paquet lameenc (pip install lameenc) ; l'application "
              "téléchargée l'inclut.",
        "de": "Zum Speichern als MP3 wird das Paket lameenc benötigt (pip install lameenc); der App-Download "
              "enthält es.",
        "es": "Para guardar MP3 hace falta el paquete lameenc (pip install lameenc); la aplicación descargada lo "
              "incluye.",
        "it": "Per salvare MP3 serve il pacchetto lameenc (pip install lameenc); l'app scaricata lo include."},
    "Reading options": {"nl": "Voorleesopties", "fr": "Options de lecture", "de": "Vorleseoptionen",
                        "es": "Opciones de lectura", "it": "Opzioni di lettura"},
    "Mark what is being read": {"nl": "Markeren wat er voorgelezen wordt", "fr": "Marquer ce qui est lu",
                                "de": "Markieren, was vorgelesen wird", "es": "Marcar lo que se está leyendo",
                                "it": "Evidenzia ciò che viene letto"},
    "The reading ruler follows the voice (focus mode)": {
        "nl": "De leeslineaal volgt de stem (focusmodus)", "fr": "La règle de lecture suit la voix (mode concentration)",
        "de": "Das Leselineal folgt der Stimme (Fokusmodus)", "es": "La regla de lectura sigue la voz (modo concentración)",
        "it": "Il righello di lettura segue la voce (modalità concentrazione)"},
    "Tap to read: on (tap a paragraph to read from there)": {
        "nl": "Tikken om voor te lezen: aan (tik op een alinea om vanaf daar voor te lezen)",
        "fr": "Toucher pour lire : activé (touchez un paragraphe pour lire à partir de là)",
        "de": "Tippen zum Vorlesen: an (tippen Sie auf einen Absatz, um ab dort vorzulesen)",
        "es": "Tocar para leer: activado (toque un párrafo para leer desde ahí)",
        "it": "Tocca per leggere: attivo (tocca un paragrafo per leggere da lì)"},
    "Tap to read: off (the text is one continuous page; taps do nothing)": {
        "nl": "Tikken om voor te lezen: uit (de tekst is één doorlopende pagina; tikken doet niets)",
        "fr": "Toucher pour lire : désactivé (le texte est une page continue ; toucher ne fait rien)",
        "de": "Tippen zum Vorlesen: aus (der Text ist eine fortlaufende Seite; Tippen bewirkt nichts)",
        "es": "Tocar para leer: desactivado (el texto es una página continua; tocar no hace nada)",
        "it": "Tocca per leggere: disattivo (il testo è una pagina continua; toccare non fa nulla)"},
    "Exit read along": {"nl": "Meelezen verlaten", "fr": "Quitter la lecture accompagnée", "de": "Mitlesen beenden",
                        "es": "Salir de la lectura guiada", "it": "Esci dalla lettura guidata"},
    "Back to where you came from": {"nl": "Terug naar waar u was", "fr": "Revenir là où vous étiez",
                                    "de": "Zurück dorthin, wo Sie waren", "es": "Volver a donde estaba",
                                    "it": "Torna dove eri"},
    "Save WAV": {"nl": "WAV opslaan", "fr": "Enregistrer le WAV", "de": "WAV speichern", "es": "Guardar WAV",
                 "it": "Salva WAV"},
    "The MP3 encoder (lameenc) could not be loaded by the Python running this app, so the audio is saved as WAV (larger). To get MP3, run this command and restart the app:": {
        "nl": "De MP3-encoder (lameenc) kon niet geladen worden door de Python waarmee deze app draait, dus de audio "
              "wordt als WAV (groter) opgeslagen. Voor MP3: voer deze opdracht uit en start de app opnieuw:",
        "fr": "L'encodeur MP3 (lameenc) n'a pas pu être chargé par le Python qui exécute cette application ; l'audio "
              "est donc enregistré en WAV (plus lourd). Pour obtenir du MP3, lancez cette commande et redémarrez "
              "l'application :",
        "de": "Der MP3-Encoder (lameenc) konnte von dem Python, mit dem diese App läuft, nicht geladen werden; das "
              "Audio wird daher als WAV (größer) gespeichert. Für MP3 diesen Befehl ausführen und die App neu starten:",
        "es": "El codificador MP3 (lameenc) no se pudo cargar en el Python que ejecuta esta aplicación, así que el "
              "audio se guarda como WAV (más grande). Para obtener MP3, ejecute este comando y reinicie la "
              "aplicación:",
        "it": "Il codificatore MP3 (lameenc) non è stato caricato dal Python che esegue questa app, quindi l'audio "
              "viene salvato come WAV (più grande). Per avere l'MP3, esegui questo comando e riavvia l'app:"},
    "The pages follow the voice": {"nl": "De pagina's volgen de stem", "fr": "Les pages suivent la voix",
                                   "de": "Die Seiten folgen der Stimme", "es": "Las páginas siguen la voz",
                                   "it": "Le pagine seguono la voce"},
    "Skip citations": {"nl": "Verwijzingen overslaan", "fr": "Ignorer les citations", "de": "Zitate überspringen",
                       "es": "Omitir citas", "it": "Salta le citazioni"},
    "Leave out citations in the text, like (Smith, 2019) and [3]. Most are found, but some unusual ones may still be read.": {
        "nl": "Verwijzingen in de tekst weglaten, zoals (Smith, 2019) en [3]. De meeste worden gevonden, maar "
              "sommige ongewone kunnen toch voorgelezen worden.",
        "fr": "Ne pas lire les citations dans le texte, comme (Smith, 2019) et [3]. La plupart sont trouvées, mais "
              "certaines inhabituelles peuvent encore être lues.",
        "de": "Zitate im Text auslassen, wie (Smith, 2019) und [3]. Die meisten werden gefunden, aber einige "
              "ungewöhnliche werden vielleicht doch vorgelesen.",
        "es": "Omitir las citas en el texto, como (Smith, 2019) y [3]. Se encuentran casi todas, pero algunas poco "
              "habituales pueden leerse igualmente.",
        "it": "Tralascia le citazioni nel testo, come (Smith, 2019) e [3]. Quasi tutte vengono trovate, ma alcune "
              "insolite potrebbero essere lette comunque."},
    "Skip references and notes": {"nl": "Literatuur en noten overslaan", "fr": "Ignorer références et notes",
                                  "de": "Literatur und Anmerkungen überspringen", "es": "Omitir referencias y notas",
                                  "it": "Salta riferimenti e note"},
    "Stop before the reference list and the notes at the end": {
        "nl": "Stoppen voor de literatuurlijst en de noten aan het eind",
        "fr": "S'arrêter avant la bibliographie et les notes à la fin",
        "de": "Vor dem Literaturverzeichnis und den Anmerkungen am Ende aufhören",
        "es": "Parar antes de la lista de referencias y las notas del final",
        "it": "Fermarsi prima della bibliografia e delle note alla fine"},
    "Mark what is read": {"nl": "Markeren wat er gelezen wordt", "fr": "Marquer ce qui est lu",
                          "de": "Markieren, was gelesen wird", "es": "Marcar lo que se lee", "it": "Evidenzia ciò che si legge"},
    "Mark the sentence and word being read": {"nl": "De zin en het woord markeren die voorgelezen worden",
                                              "fr": "Marquer la phrase et le mot en cours de lecture",
                                              "de": "Den Satz und das Wort markieren, die vorgelesen werden",
                                              "es": "Marcar la frase y la palabra que se están leyendo",
                                              "it": "Evidenzia la frase e la parola che vengono lette"},
    "Ruler follows the voice": {"nl": "Lineaal volgt de stem", "fr": "La règle suit la voix",
                                "de": "Lineal folgt der Stimme", "es": "La regla sigue la voz",
                                "it": "Il righello segue la voce"},
    "In focus mode, the reading ruler moves along with the voice": {
        "nl": "In de focusmodus beweegt de leeslineaal mee met de stem",
        "fr": "En mode concentration, la règle de lecture avance avec la voix",
        "de": "Im Fokusmodus bewegt sich das Leselineal mit der Stimme",
        "es": "En el modo concentración, la regla de lectura avanza con la voz",
        "it": "In modalità concentrazione il righello di lettura si muove con la voce"},
    "Enjoying the app? It is free and made by one person. A small donation helps keep it going.": {
        "nl": "Heb je iets aan de app? Hij is gratis en gemaakt door één persoon. Een kleine donatie helpt hem "
              "verder te maken.",
        "fr": "L'application vous plaît ? Elle est gratuite et faite par une seule personne. Un petit don aide à la "
              "faire vivre.",
        "de": "Gefällt Ihnen die App? Sie ist kostenlos und von einer Person gemacht. Eine kleine Spende hilft, sie "
              "weiterzuführen.",
        "es": "¿Le gusta la aplicación? Es gratuita y la hace una sola persona. Un pequeño donativo ayuda a "
              "mantenerla.",
        "it": "Ti piace l'app? È gratuita e fatta da una sola persona. Una piccola donazione aiuta a portarla "
              "avanti."},
    "Donate": {"nl": "Doneren", "fr": "Faire un don", "de": "Spenden", "es": "Donar", "it": "Dona"},
    "Don't show again": {"nl": "Niet meer tonen", "fr": "Ne plus afficher", "de": "Nicht mehr zeigen",
                         "es": "No volver a mostrar", "it": "Non mostrare più"},
    "A small reminder now and then (every 10 starts)": {
        "nl": "Af en toe een kleine herinnering (elke 10 keer starten)",
        "fr": "Un petit rappel de temps en temps (tous les 10 démarrages)",
        "de": "Ab und zu eine kleine Erinnerung (alle 10 Starts)",
        "es": "Un pequeño recordatorio de vez en cuando (cada 10 inicios)",
        "it": "Un piccolo promemoria ogni tanto (ogni 10 avvii)"},
    "Continuous page: the text as one long page, from here (Exit read along comes back to the pages)": {
        "nl": "Doorlopende pagina: de tekst als één lange pagina, vanaf hier (Meelezen verlaten brengt je terug "
              "naar de pagina's)",
        "fr": "Page continue : le texte en une seule longue page, à partir d'ici (Quitter la lecture accompagnée "
              "ramène aux pages)",
        "de": "Fortlaufende Seite: der Text als eine lange Seite, ab hier (Mitlesen beenden führt zurück zu den "
              "Seiten)",
        "es": "Página continua: el texto como una sola página larga, desde aquí (Salir de la lectura guiada vuelve "
              "a las páginas)",
        "it": "Pagina continua: il testo come un'unica lunga pagina, da qui (Esci dalla lettura guidata torna alle "
              "pagine)"},
    "Follow pages": {"nl": "Pagina's volgen", "fr": "Suivre les pages", "de": "Seiten folgen", "es": "Seguir páginas",
                     "it": "Segui le pagine"},
    "Turn pages along: the pages follow the voice": {
        "nl": "Pagina's mee omslaan: de pagina's volgen de stem", "fr": "Tourner les pages : les pages suivent la voix",
        "de": "Seiten mitblättern: die Seiten folgen der Stimme", "es": "Pasar las páginas: las páginas siguen la voz",
        "it": "Girare le pagine: le pagine seguono la voce"},
    "Skip references": {"nl": "Literatuur overslaan", "fr": "Ignorer les références", "de": "Literatur überspringen",
                        "es": "Omitir referencias", "it": "Salta i riferimenti"},
    "Skip the reference list and notes: stop before them at the end": {
        "nl": "De literatuurlijst en noten overslaan: stoppen voor ze aan het eind beginnen",
        "fr": "Ignorer la bibliographie et les notes : s'arrêter avant elles à la fin",
        "de": "Literaturverzeichnis und Anmerkungen überspringen: am Ende davor aufhören",
        "es": "Omitir la lista de referencias y las notas: parar antes de ellas al final",
        "it": "Salta la bibliografia e le note: fermarsi prima di esse alla fine"},
    "Mark reading": {"nl": "Lezen markeren", "fr": "Marquer la lecture", "de": "Lesen markieren", "es": "Marcar lectura",
                     "it": "Evidenzia lettura"},
    "Ruler follows": {"nl": "Lineaal volgt", "fr": "Règle suit", "de": "Lineal folgt", "es": "Regla sigue",
                      "it": "Righello segue"},
    "Ruler follows the voice: in focus mode, the reading ruler moves along with it": {
        "nl": "Lineaal volgt de stem: in de focusmodus beweegt de leeslineaal mee",
        "fr": "La règle suit la voix : en mode concentration, la règle de lecture avance avec elle",
        "de": "Lineal folgt der Stimme: im Fokusmodus bewegt sich das Leselineal mit",
        "es": "La regla sigue la voz: en el modo concentración, la regla de lectura avanza con ella",
        "it": "Il righello segue la voce: in modalità concentrazione il righello di lettura si muove con essa"},
    "Python: {path}": {"nl": "Python: {path}", "fr": "Python : {path}", "de": "Python: {path}", "es": "Python: {path}",
                       "it": "Python: {path}"},
    "not available in this copy of the app": {"nl": "niet beschikbaar in deze versie van de app",
                                              "fr": "non disponible dans cette copie de l'application",
                                              "de": "in dieser Kopie der App nicht verfügbar",
                                              "es": "no disponible en esta copia de la aplicación",
                                              "it": "non disponibile in questa copia dell'app"},
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
    "unusual_layout": {
        "nl": "Pagina('s) {0} van de pdf hebben een ongewone opmaak (een kader of citaat over de kolommen heen); "
              "de app las ze kolom per kolom. Vergelijk met het origineel in de weergave Beide.",
        "fr": "La/les page(s) {0} du PDF ont une mise en page inhabituelle (un encadré ou une citation à cheval "
              "sur les colonnes) ; l'application les a lues colonne par colonne. Comparez avec l'original dans la "
              "vue Les deux.",
        "de": "Seite(n) {0} des PDFs haben ein ungewöhnliches Layout (ein Kasten oder Zitat über die Spalten "
              "hinweg); die App hat sie Spalte für Spalte gelesen. Vergleichen Sie mit dem Original in der Ansicht "
              "Beide.",
        "es": "La(s) página(s) {0} del PDF tienen un diseño poco habitual (un recuadro o una cita que cruza las "
              "columnas); la aplicación las leyó columna por columna. Compáralo con el original en la vista Ambos.",
        "it": "La/le pagina/e {0} del PDF hanno un'impaginazione insolita (un riquadro o una citazione a cavallo "
              "delle colonne); l'app le ha lette colonna per colonna. Confronta con l'originale nella vista "
              "Entrambi."},
    "sent_to_ai": {"nl": "Naar AI gestuurd: {0}", "fr": "Envoyé à l'IA : {0}", "de": "An die KI gesendet: {0}",
                   "es": "Enviado a la IA: {0}", "it": "Inviato all'IA: {0}"},
    "n_citations": {"nl": "{0} twijfelachtige verwijzing(en)", "fr": "{0} citation(s) incertaine(s)",
                    "de": "{0} unsichere(s) Zitat(e)", "es": "{0} cita(s) dudosa(s)",
                    "it": "{0} citazione/i incerta/e"},
    "n_layout_pages": {"nl": "{0} pagina('s) met een ongewone opmaak",
                       "fr": "{0} page(s) à la mise en page inhabituelle",
                       "de": "{0} Seite(n) mit ungewöhnlichem Layout", "es": "{0} página(s) con un diseño poco habitual",
                       "it": "{0} pagina/e con un'impaginazione insolita"},
    "n_splits": {"nl": "{0} woord(en) dat door een spatie gesplitst kan zijn ({1} samengevoegd)",
                 "fr": "{0} mot(s) peut-être coupé(s) par une espace ({1} réuni(s))",
                 "de": "{0} Wort/Wörter, evtl. durch ein Leerzeichen getrennt ({1} zusammengefügt)",
                 "es": "{0} palabra(s) quizá separada(s) por un espacio ({1} unida(s))",
                 "it": "{0} parola/e forse divisa/e da uno spazio ({1} unita/e)"},
    "n_ocr_words": {"nl": "{0} twijfelachtig(e) OCR-woord(en)", "fr": "{0} mot(s) OCR incertain(s)",
                    "de": "{0} unsichere(s) OCR-Wort/Wörter", "es": "{0} palabra(s) OCR dudosa(s)",
                    "it": "{0} parola/e OCR incerta/e"},
    "check_part": {"nl": "Deel {0} van {1} wordt gecontroleerd", "fr": "Vérification de la partie {0} sur {1}",
                   "de": "Teil {0} von {1} wird geprüft", "es": "Revisando la parte {0} de {1}",
                   "it": "Controllo della parte {0} di {1}"},
    "font_substitute": {
        "nl": "{0} is niet geïnstalleerd op dit apparaat; in de plaats wordt het gelijkaardige gratis lettertype "
              "{1} gebruikt.",
        "fr": "{0} n'est pas installée sur cet appareil ; la police libre similaire {1} est utilisée à la place.",
        "de": "{0} ist auf diesem Gerät nicht installiert; stattdessen wird die ähnliche freie Schrift {1} "
              "verwendet.",
        "es": "{0} no está instalada en este dispositivo; se usa en su lugar la fuente libre similar {1}.",
        "it": "{0} non è installato su questo dispositivo; al suo posto si usa il carattere libero simile {1}."},
}
