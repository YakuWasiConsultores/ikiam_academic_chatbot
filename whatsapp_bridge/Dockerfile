FROM node:20-alpine

WORKDIR /app

# Instalar dependencias
COPY package*.json ./
RUN npm install --omit=dev

# Copiar código fuente del puente
COPY bridge.js ./

# Puerto del visor web QR
EXPOSE 3001

# Variables de entorno
ENV NODE_ENV=production
ENV PORT=3001
ENV API_ENDPOINT=https://ikiam-academic-chatbot.onrender.com/api/chat

# Ejecutar proceso principal
CMD ["node", "bridge.js"]
