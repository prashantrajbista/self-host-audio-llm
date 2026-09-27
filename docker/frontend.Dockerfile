FROM node:20-alpine AS builder
WORKDIR /app
COPY client/package.json client/package-lock.json* ./
RUN npm install
COPY client/ .
ARG NEXT_PUBLIC_GATEWAY_WS_URL
ENV NEXT_PUBLIC_GATEWAY_WS_URL=${NEXT_PUBLIC_GATEWAY_WS_URL}
RUN npm run build

FROM node:20-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["npm", "run", "start"]
