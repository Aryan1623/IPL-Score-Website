# IPL Score Website

Static website built with HTML, CSS, and JavaScript.

## What it does

- displays IPL match results from the downloaded Cricsheet IPL archive
- lets you filter by season and team
- lets you search by team short name, full team name, city, venue, or result text
- deploys automatically to GitHub Pages through GitHub Actions on every push to `main`
- runs deterministic tests before deployment
- can generate additional AI-assisted tests from each code diff in CI

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

## Test pipeline

The workflow now has three stages:

1. deterministic Python tests for the data-building logic
2. AI-assisted test generation from the current git diff
3. deployment to GitHub Pages only after the earlier stages pass

## Enable AI-generated test cases

The AI test generator script lives at:

`scripts/generate_ai_test_cases.py`

To turn on real AI generation in GitHub Actions, add these repository secrets:

- `AI_TEST_API_KEY`
- `AI_TEST_MODEL`

Optional:

- `AI_TEST_API_URL` if you are using a non-default OpenAI-compatible endpoint

Optional repository variables:

- `AI_TEST_REQUIRED=true` to fail CI when AI test generation cannot run

How it works:

- GitHub Actions checks the changed files in the current push or pull request
- the script sends only those changed code files to the AI model
- the model returns executable Python `unittest` files or manual check suggestions
- generated tests are stored as workflow artifacts and run automatically when executable Python tests are produced

Important note:

AI-generated tests are useful as an extra regression layer, but they should support your trusted baseline tests rather than replace them.
