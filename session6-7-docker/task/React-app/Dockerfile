# ---------- stage 1: build ----------
# node_modules for a React app is hundreds of MB. None of it is needed at
# runtime - the browser only ever receives the compiled bundle.
FROM node:22-alpine AS builder

WORKDIR /build
COPY package.json ./
RUN npm install

COPY index.html vite.config.js ./
COPY src ./src
RUN npm run build          # writes /build/dist

# ---------- stage 2: runtime ----------
FROM nginx:alpine

# Only dist/ crosses the stage boundary. No Node, no npm, no node_modules.
COPY --from=builder /build/dist /usr/share/nginx/html

EXPOSE 80
