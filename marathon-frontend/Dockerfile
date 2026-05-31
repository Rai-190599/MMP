# ── Stage 1: build ──────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (layer cache)
COPY package.json package-lock.json ./
RUN npm ci --silent

# Copy source and build
# VITE_* vars must be available at build time — passed via --build-arg
ARG VITE_API_URL=http://localhost:8000
ARG VITE_EVENT_ID=aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_EVENT_ID=$VITE_EVENT_ID

COPY . .
RUN npm run build

# ── Stage 2: serve ───────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Remove default nginx page
RUN rm -rf /usr/share/nginx/html/*

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx config: serve SPA, proxy /auth /events /registrations /organizer /volunteers to api
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
