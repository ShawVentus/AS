FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy app code
COPY . .

# Expose port
EXPOSE 5173

# Command is set in docker-compose
CMD ["npm", "run", "dev", "--", "--host"]
