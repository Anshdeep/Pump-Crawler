FROM node:18-alpine

WORKDIR /app

# Copy dependency manifest files and install
COPY package*.json ./
RUN npm install

# Copy frontend source files
COPY . .

# Expose Vite port
EXPOSE 5173

# Start Vite dev server on host 0.0.0.0 to make it accessible outside container
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
