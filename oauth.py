"""Mercado Libre OAuth authorization-code flow for Streamlit Cloud."""
import hashlib
import hmac
import secrets
import time
from urllib.parse import urlencode
import requests
import streamlit as st

AUTHORIZE = "https://auth.mercadolibre.com.ar/authorization"
TOKEN_URL = "https://api.mercadolibre.com/oauth/token"

def config():
    try:
        return (st.secrets["MELI_CLIENT_ID"], st.secrets["MELI_CLIENT_SECRET"],
                st.secrets["MELI_REDIRECT_URI"])
    except (KeyError, FileNotFoundError):
        return None

def make_state(secret):
    stamp = str(int(time.time()))
    nonce = secrets.token_urlsafe(24)
    payload = stamp + "." + nonce
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return payload + "." + signature

def valid_state(value, secret):
    try:
        stamp, nonce, signature = value.split(".")
        payload = stamp + "." + nonce
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return (0 <= time.time() - int(stamp) <= 600
                and hmac.compare_digest(signature, expected))
    except (ValueError, AttributeError, TypeError):
        return False

def authorization_url(settings):
    client_id, client_secret, redirect = settings
    return AUTHORIZE + "?" + urlencode({
        "response_type": "code", "client_id": client_id,
        "redirect_uri": redirect, "state": make_state(client_secret)
    })

def exchange(settings, **fields):
    client_id, client_secret, redirect = settings
    payload = {"grant_type": fields.pop("grant_type"), "client_id": client_id,
               "client_secret": client_secret, **fields}
    if payload["grant_type"] == "authorization_code":
        payload["redirect_uri"] = redirect
    try:
        response = requests.post(TOKEN_URL, data=payload, timeout=15)
        response.raise_for_status()
        result = response.json()
        if not result.get("access_token"):
            raise ValueError("Mercado Libre no devolvió un access token.")
        return result
    except (requests.RequestException, ValueError) as exc:
        raise ValueError("No se pudo completar la autorización con Mercado Libre.") from exc

def store_tokens(result):
    st.session_state.meli_access_token = result["access_token"]
    st.session_state.meli_refresh_token = result.get("refresh_token", "")
    st.session_state.meli_expires_at = time.time() + int(result.get("expires_in", 21600))

def callback(settings):
    params = st.query_params
    if "error" in params:
        st.query_params.clear()
        st.error("Mercado Libre rechazó o canceló la autorización.")
    elif "code" in params:
        code, state = params.get("code"), params.get("state")
        st.query_params.clear()  # Never leave authorization code in the URL.
        if not valid_state(state, settings[1]):
            st.error("La autorización venció o no pasó la validación de seguridad. Volvé a conectar.")
            return
        try:
            store_tokens(exchange(settings, grant_type="authorization_code", code=code))
            st.success("Mercado Libre conectado en esta sesión.")
        except ValueError as exc:
            st.error(str(exc))

def access_token(settings):
    token = st.session_state.get("meli_access_token", "")
    if not token:
        return ""
    if time.time() < st.session_state.get("meli_expires_at", 0) - 60:
        return token
    refresh = st.session_state.get("meli_refresh_token", "")
    if not refresh:
        st.session_state.meli_access_token = ""
        return ""
    try:
        store_tokens(exchange(settings, grant_type="refresh_token", refresh_token=refresh))
        return st.session_state.meli_access_token
    except ValueError:
        st.session_state.meli_access_token = ""
        st.session_state.meli_refresh_token = ""
        return ""
