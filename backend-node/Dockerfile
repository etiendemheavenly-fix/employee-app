FROM node:22-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    iputils-ping curl netcat-openbsd dnsutils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package.json .
RUN npm install --omit=dev

COPY app.js .

EXPOSE 5000

CMD ["node", "app.js"]
