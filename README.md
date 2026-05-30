# IPL Score Website

Static website built with HTML, CSS, and JavaScript.

## What it does

- displays IPL match results from the downloaded Cricsheet IPL archive
- lets you filter by season and team
- lets you search by team short name, full team name, city, venue, or result text

## Project structure

- `index.html` for markup
- `styles.css` for styling
- `app.js` for rendering and filtering
- `data/matches.json` for the frontend data source
- `scripts/build_ipl_data.py` to regenerate the frontend data from the raw archive

## Regenerate the dataset

From the `IPL Score Website` folder:

```bash
python3 scripts/build_ipl_data.py
```
