FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
FROM node:22-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
EXPOSE 4321
CMD ["npx","astro","preview","--host","0.0.0.0","--port","4321"]
