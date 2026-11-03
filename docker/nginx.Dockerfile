FROM nginx:1.27-alpine

RUN apk add --no-cache openssl

RUN mkdir -p /etc/nginx/certs \
    && openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
        -keyout /etc/nginx/certs/privkey.pem \
        -out /etc/nginx/certs/fullchain.pem \
        -subj "/CN=101.254.157.190" \
        -addext "subjectAltName=IP:101.254.157.190"\
    && chmod 600 /etc/nginx/certs/privkey.pem

COPY docker/nginx.conf /etc/nginx/nginx.conf

EXPOSE 443

# CMD ["nginx", "-g", "daemon off;"]