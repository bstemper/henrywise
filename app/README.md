# UK Take-Home Pay Calculator (2026/27)

A small Streamlit app. Enter a salary + a few options, get take-home pay.

## Run it locally
1. Install Python 3.9+
2. `pip install -r requirements.txt`
3. `streamlit run app.py`
   A browser tab opens at http://localhost:8501

## Deploy it free (public link, private code)
1. Push these files to a GitHub repo (it can be private).
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Click "Create app", pick your repo + `app.py`, and Deploy.
   You get a public `*.streamlit.app` URL in a couple of minutes.

## Where to edit things
All tax figures are in the `TAX_YEAR` dict at the top of `app.py`.
That's the only place you change each April when rates update.

Estimate only — not financial advice. See the in-app "What this covers" note.
