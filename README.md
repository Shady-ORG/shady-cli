# Shady CLI

Shady ist ein CLI-Tool zum lokalen Spiegeln (Mirror) von Web-Ressourcen inklusive Source-Metadaten.

## Installation

### Mit Make

```bash
make install
```

Danach z. B.:

```bash
shady-cli --help
```

### Direkt mit pip

```bash
python3 -m pip install --user -e .
```

## Command-Doku

Das Tool läuft direkt über den Root-Command (kein Subcommand nötig):

```bash
shady-cli -u https://site.tld -s --result ./out --max-pages 200 --scope same-origin
```

Wenn du den Alias `shady` gesetzt hast:

```bash
shady -u https://site.tld -s --result ./out
```

### Wichtige Optionen

- `-u, --url` Start-URL
- `-s, --sources` aktiviert Source-Metadaten-Ausgabe
- `--result` Output-Ordner (Default: `./out`)
- `--max-pages` maximale Anzahl Pages
- `--scope` `same-origin|same-host|all`
- `--include-assets` z. B. `js,css,img,font`
- `--respect-robots` reserviert für robots.txt Verhalten
- `--depth` Crawl-Tiefe
- `--concurrency` parallele Requests
- `--rate` Rate-Limit, z. B. `5rps`
- `--rewrite-links` Links für Offline-Browsing umschreiben
- `--store-raw` rohe Responses zusätzlich speichern

### Help mit allen neuen Args

```bash
shady-cli --help
```

## Beispiele

### 1) Basis-Mirror mit Sources

```bash
shady-cli -u https://example.com -s --result ./out
```

### 2) Strenger Scope + begrenzte Tiefe

```bash
shady-cli -u https://example.com --scope same-origin --depth 2 --max-pages 50
```

### 3) Nur bestimmte Assets + Raw speichern

```bash
shady-cli -u https://example.com --include-assets js,css --store-raw true
```

## Output-Struktur

```text
out/
  mirror/
    site.tld/
      _meta/
        crawl.jsonl
        errors.jsonl
        summary.json
      pages/
      assets/
      raw/        # nur mit --store-raw
```

## Was extrahiert wird

- HTML Pages
- JS/CSS/Images/Fonts (gemäss `--include-assets`)
- Inline-Script-Hinweise
- Externe Script-URLs
- `sourceMappingURL` Hinweise
- JS Imports (best effort)
- Netzwerk-Hints (`fetch`, `axios.*`) als Metadaten
- Formular-Metadaten (`action`, `method`, Inputs)

## Uninstall

```bash
make uninstall
```
