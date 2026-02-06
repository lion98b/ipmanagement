\
# IP Monitor (Tkinter) — versione modularizzata

Questa repo è la versione segmentata del tuo monolite Tkinter.

## Avvio
```bash
python -m pip install -r requirements.txt
python main.py
```

## Config
- `config.cfg` (dispositivi)
- `settings.cfg` (impostazioni app)
- `report_state.json` (stato report)

## Pubblicare su GitHub (tuo account)
1) Crea un repo vuoto su GitHub (senza README).
2) Da terminale, nella cartella del progetto:

```bash
git init
git add .
git commit -m "Initial modularized version"
git branch -M main
git remote add origin https://github.com/<TUO_UTENTE>/<NOME_REPO>.git
git push -u origin main
```

Se usi SSH cambia l'URL remote.
