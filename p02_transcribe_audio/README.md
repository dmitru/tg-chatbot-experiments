# What is it?

Telegram chatbot for speech-to-text conversion using Whisper model running on Replicate.io

# How to run

1. Copy .env.template to .env, fill it out
2. Create google_service_key.json, fill it out (https://docs.gspread.org/en/v5.7.1/oauth2.html#enable-api-access-for-a-project)
3. Create a venv, Python 3.10, activate it: `python3 -m venv .venv` then `source .venv/bin/activate`
4. Install packages: `pip install -r requirements.txt`
5. Run it! `python ./main.py`

# Deployment

As of 2023-07-24 it's deployed to a Digitalocean droplet, Ubuntu 22.04.
