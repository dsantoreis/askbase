# Askbase Docs — Conversão para Astro Starlight

![Hero](./public/assets/hero.svg)
![Demo GIF](./public/assets/demo.gif)

[![Docs CI](https://img.shields.io/github/actions/workflow/status/dsantoreis/askbase/docs-site.yml?branch=main)](../../actions/workflows/docs-site.yml)

## Quickstart
```bash
npm ci
npm run dev
npm run build
```

## Docker
```bash
docker build -t askbase-docs:latest .
docker compose up --build
```

## Kubernetes
```bash
kubectl apply -f k8s/
```
