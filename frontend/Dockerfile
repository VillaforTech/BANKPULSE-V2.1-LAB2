FROM nginx:1.27-alpine
LABEL org.opencontainers.image.title="BANKdragon BankPulse V2.1 Interactive Banking"
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html styles.css app.js /usr/share/nginx/html/
COPY assets /usr/share/nginx/html/assets
EXPOSE 8080
