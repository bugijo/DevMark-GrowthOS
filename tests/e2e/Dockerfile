FROM mcr.microsoft.com/playwright:v1.61.1-noble

WORKDIR /work
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run typecheck

CMD ["npm", "test"]
