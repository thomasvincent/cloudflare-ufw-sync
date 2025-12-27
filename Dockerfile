FROM python:3.13-slim

# Update system packages to get latest security patches
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Install the package
RUN pip install -e .

# Run the application
ENTRYPOINT ["cloudflare-ufw-sync"]
CMD ["--help"]