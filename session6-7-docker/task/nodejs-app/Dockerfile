FROM node:22-alpine

WORKDIR /app

# Copy the manifest first so `npm install` is only re-run when dependencies
# change, not on every source edit. This is the layer-cache win.
COPY package.json ./
RUN npm install --omit=dev

COPY index.js ./

EXPOSE 3000
CMD ["node", "index.js"]
