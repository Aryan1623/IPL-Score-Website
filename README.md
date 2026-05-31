# IPL Score Website

Static website built with HTML, CSS, and JavaScript.

## What it does

- displays IPL match results from the downloaded Cricsheet IPL archive
- lets you filter by season and team
- lets you search by team short name, full team name, city, venue, or result text
- deploys automatically to GitHub Pages through GitHub Actions on every push to `main`

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

The script can rebuild from the extracted JSON files or automatically unpack `data/raw/ipl_json.zip` when needed.

## Automatic deployment

The GitHub Actions workflow lives at:

`/.github/workflows/deploy.yml`

To enable deployment in GitHub:

1. Open your repository on GitHub.
2. Go to `Settings` -> `Pages`.
3. Under `Build and deployment`, set `Source` to `GitHub Actions`.

After that, every push to `main` will rebuild the dataset and deploy the website automatically.
