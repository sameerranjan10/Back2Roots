#!/bin/bash
# ══════════════════════════════════════════════════════════
#  ssl_gen.sh — Generate a self-signed SSL certificate for
#  local development.
#
#  Usage:  bash ssl_gen.sh
#  Output: ssl/cert.pem  ssl/key.pem
#
#  For production use Let's Encrypt / Certbot instead:
#    certbot --nginx -d yourdomain.com
# ══════════════════════════════════════════════════════════
set -e

SSL_DIR="ssl"
mkdir -p "$SSL_DIR"

echo "🔐 Generating self-signed SSL certificate..."

openssl req -x509 \
  -nodes \
  -days 365 \
  -newkey rsa:2048 \
  -keyout "$SSL_DIR/key.pem" \
  -out    "$SSL_DIR/cert.pem" \
  -subj   "/C=IN/ST=Maharashtra/L=Mumbai/O=AlumniNexus/OU=Dev/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

echo ""
echo "✅ Certificate generated:"
echo "   Certificate : $SSL_DIR/cert.pem"
echo "   Private key : $SSL_DIR/key.pem"
echo ""
echo "⚠️  This is a SELF-SIGNED certificate for development only."
echo "   Browsers will show a security warning — click 'Advanced' → 'Proceed'."
echo "   For production, use Let's Encrypt: https://certbot.eff.org"
