# =============================================================================
# Frontend Dockerfile — CodeLens React UI
# =============================================================================
# Multi-stage build:
#   1. Node builder → npm install + vite build
#   2. Nginx runtime → serve the static bundle
#
# Build:   docker build -t sse-frontend ./frontend
# Run:     docker run -p 3000:80 sse-frontend
# =============================================================================

# ── Stage 1: Build ───────────────────────────────────────────────────────────

FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (layer cache optimization)
COPY package.json package-lock.json* ./
RUN npm ci --silent 2>/dev/null || npm install --silent

# Copy source and build
COPY . .

# Build-time env: the backend URL injected at build time
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ── Stage 2: Serve with Nginx ────────────────────────────────────────────────

FROM nginx:1.27-alpine AS runtime

LABEL maintainer="Krishna"
LABEL description="Semantic Code Search Engine - React Frontend"

# Remove default nginx content
RUN rm -rf /usr/share/nginx/html/*

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Custom nginx config for SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q --spider http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
