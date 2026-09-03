# Build
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci        
# npm ci = Clean Install     Designed for CI/Docker/production builds

COPY . .
RUN npm run build

# Serve
FROM nginx:alpine
 
COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]