# De Ambitiebol — KTV 2026–2027

Werkende Nederlandstalige webapp voor een workshop met **anonieme individuele reflectie**, **live groeiende themabollen**, **QR-code**, **hostbediening**, **groepsconcretisering van de twee grootste bollen** en **JSON-export**.

## Starten

Vereist Python 3.10+ en QR-code bibliotheek:

```bash
pip install -r requirements.txt
export HOST_KEY='kies-een-lang-uniek-geheim'  # Windows PowerShell: $env:HOST_KEY='...'
python server.py
```

Open `http://localhost:8080/host?key=kies-een-lang-uniek-geheim` op je eigen computer. Deelnemers gebruiken `/join?code=SESSIECODE` via de host-QR-code.

## Telefoons en hosting

Een telefoon kan `localhost` op je computer niet openen. Voor gebruik op school moet de site vanaf de telefoon bereikbaar zijn via een **HTTPS-domein**, of lokaal via het IP-adres van de server op hetzelfde netwerk (mits apparaten met elkaar mogen communiceren). Voor HTTPS-publicatie kan de app op een Python-hostingplatform met persistent opslagvolume worden uitgevoerd met `python server.py` en een ingestelde `PORT` en `HOST_KEY`.

**Data**: De app slaat anonieme deelnemers-ID's en antwoorden lokaal op in `workshop-data.json` (of het pad in `DATA_FILE`). Bij hosting zonder blijvende opslag gaan resultaten verloren na serverherstart. Zet geen openbare hosting op zonder persistente opslag als de gegevens bewaard moeten blijven. De hostsleutel is nodig om een sessie te beheren en resultaten te exporteren; deel die URL niet met deelnemers.

## Werking

- 3 thema's, elk 5 stellingen, geformuleerd op basis van de Teamambitie 2024–2025.
- Beoordeling 1–4: gewenste **extra aandacht voor de komende acht weken**, niet het intrinsieke belang.
- Bollen tonen het gemiddelde van de afgegeven beoordelingen binnen een thema. Alle thema's blijven zichtbaar. Een lage bol betekent niet 'onbelangrijk'.
- Host verandert fases: reflectie → bespreken → groepsfase → afgerond.
- In de groepsfase zijn automatisch de twee hoogste thema's selecteerbaar. Groepjes dienen concrete acties, routines en waarneembare signalen in.
- Host kan een resultatenexport openen (`/api/export?key=...`) of een nieuwe sessie starten. Een reset verwijdert alle oude sessiegegevens.

## Veiligheids- en praktische opmerkingen

Deelnemers krijgen een anonieme browser-ID; dit is geen authenticatie. Een deelnemer kan door cookies/gegevens te wissen opnieuw meedoen. Voor een KTV is dit meestal voldoende, maar het is geen formele enquêtebeveiliging. Deelnemersantwoorden worden tijdens de reflectie automatisch bijgewerkt. De groeibollen zijn expres geen 'verkiezingsresultaat'.
