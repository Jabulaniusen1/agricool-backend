FROM caddy:2.8.4-alpine

ENV FRONTEND_ORIGINS=app.coldtivate.org
ENV ACME_SERVER=https://acme-v02.api.letsencrypt.org/directory
ENV URL_BASE_API=https://api.coldtivate.org
ENV URL_AIR_VCCA=https://air-prod.coldtivate.org
ENV URL_FARMER_API=https://farmer-prod.coldtivate.org
ENV URL_IMPACT_API=https://impact-prod.coldtivate.org

COPY Caddyfile /etc/caddy/Caddyfile
