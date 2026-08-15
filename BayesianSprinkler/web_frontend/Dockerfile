FROM node:21-alpine AS builder

WORKDIR /app
COPY package.json .
RUN npm install

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
RUN if [ -d /usr/share/nginx/html/favicon.png ]; then rm -rf /usr/share/nginx/html/favicon.png; fi && \
    chmod -R a+rX /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]