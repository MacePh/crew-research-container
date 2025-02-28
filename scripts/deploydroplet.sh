#!/bin/bash

# deploydroplet.sh - Comprehensive deployment script for Research Crew Container on DigitalOcean
# This script handles Docker setup, environment variables, and Nginx configuration

# Text formatting
BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print section headers
print_section() {
    echo -e "\n${BOLD}${GREEN}=== $1 ===${NC}\n"
}

# Function to print warnings
print_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

# Function to print errors
print_error() {
    echo -e "${RED}ERROR: $1${NC}"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "This script must be run as root or with sudo"
    exit 1
fi

print_section "Starting Research Crew Container Deployment"

# Step 1: Check for .env file
print_section "Checking Environment Variables"
if [ -f .env ]; then
    echo "Found .env file"
    # Source the .env file to use variables in this script
    export $(grep -v '^#' .env | xargs)
else
    print_warning ".env file not found. We'll create one."
    
    # Prompt for required API keys
    echo "Please enter the following API keys:"
    read -p "SERPER_API_KEY (required): " SERPER_API_KEY
    read -p "OPENAI_API_KEY (required): " OPENAI_API_KEY
    read -p "API_KEY (for API authentication, default: dev-api-key): " API_KEY
    read -p "GITHUB_TOKEN (optional): " GITHUB_TOKEN
    
    # Set defaults for empty values
    API_KEY=${API_KEY:-dev-api-key}
    
    # Check required keys
    if [ -z "$SERPER_API_KEY" ] || [ -z "$OPENAI_API_KEY" ]; then
        print_error "SERPER_API_KEY and OPENAI_API_KEY are required"
        exit 1
    fi
    
    # Create .env file
    echo "Creating .env file..."
    cat > .env << EOF
SERPER_API_KEY=$SERPER_API_KEY
OPENAI_API_KEY=$OPENAI_API_KEY
API_KEY=$API_KEY
GITHUB_TOKEN=$GITHUB_TOKEN
EOF
    echo ".env file created successfully"
fi

# Step 2: Check Docker installation
print_section "Checking Docker Installation"
if ! command -v docker &> /dev/null; then
    print_warning "Docker not found. Installing Docker..."
    apt-get update
    apt-get install -y apt-transport-https ca-certificates curl software-properties-common
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
    add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
    apt-get update
    apt-get install -y docker-ce
    systemctl enable docker
    systemctl start docker
    echo "Docker installed successfully"
else
    echo "Docker is already installed"
fi

# Step 3: Stop and remove existing containers
print_section "Preparing Docker Environment"
echo "Stopping any existing containers..."
docker stop research-crew-container 2>/dev/null || true
docker rm research-crew-container 2>/dev/null || true

# Step 4: Build Docker image
print_section "Building Docker Image"
echo "Building Docker image..."
docker build -t research-crew -f docker/Dockerfile .

if [ $? -ne 0 ]; then
    print_error "Docker build failed"
    exit 1
fi

# Step 5: Run Docker container
print_section "Starting Docker Container"
echo "Starting container with environment variables..."
docker run -d --name research-crew-container -p 8000:8000 --env-file .env \
    --restart=always \
    research-crew uvicorn api.api:app --host 0.0.0.0 --port 8000

if [ $? -ne 0 ]; then
    print_error "Failed to start container"
    exit 1
fi

echo "Container started successfully!"

# Step 6: Check if docker0 interface is up
print_section "Checking Docker Network"
DOCKER0_STATUS=$(ip addr show docker0 2>/dev/null | grep -o "state [A-Z]*" | cut -d' ' -f2)

if [ "$DOCKER0_STATUS" = "DOWN" ]; then
    print_warning "docker0 interface is DOWN. Bringing it up..."
    ip link set docker0 up
    systemctl restart docker
    
    # Restart our container after Docker restart
    echo "Restarting our container after Docker service restart..."
    sleep 5
    docker start research-crew-container
fi

# Step 7: Install and configure Nginx
print_section "Setting Up Nginx"
if ! command -v nginx &> /dev/null; then
    echo "Installing Nginx..."
    apt-get update
    apt-get install -y nginx
else
    echo "Nginx is already installed"
fi

# Create Nginx configuration
echo "Creating Nginx configuration..."
cat > /etc/nginx/sites-available/api << 'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    
    server_name _;
    
    # Allow all origins
    add_header 'Access-Control-Allow-Origin' '*';
    add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS';
    add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization,X-API-Key';
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Add timeout and buffer settings
        proxy_connect_timeout 75s;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_buffering off;
    }
}
EOF

# Enable the site and disable default if it exists
echo "Enabling Nginx configuration..."
ln -sf /etc/nginx/sites-available/api /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
echo "Testing Nginx configuration..."
nginx -t

if [ $? -ne 0 ]; then
    print_error "Nginx configuration test failed"
    exit 1
fi

# Restart Nginx
echo "Restarting Nginx..."
systemctl restart nginx

# Step 8: Configure firewall
print_section "Configuring Firewall"
if command -v ufw &> /dev/null; then
    echo "Configuring UFW firewall..."
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 8000/tcp
    
    # Only enable UFW if it's not already enabled
    if ! ufw status | grep -q "Status: active"; then
        echo "y" | ufw enable
    fi
    
    echo "Firewall configured"
else
    print_warning "UFW not installed. Skipping firewall configuration."
fi

# Step 9: Verify deployment
print_section "Verifying Deployment"
echo "Checking if Docker container is running..."
if docker ps | grep -q "research-crew-container"; then
    echo "✅ Docker container is running"
else
    print_error "Docker container is not running"
    echo "Checking container logs:"
    docker logs research-crew-container
fi

echo "Checking if Nginx is running..."
if systemctl is-active --quiet nginx; then
    echo "✅ Nginx is running"
else
    print_error "Nginx is not running"
fi

# Get the server's public IP
SERVER_IP=$(curl -s ifconfig.me)

print_section "Deployment Complete!"
echo "Your Research Crew API should now be accessible at:"
echo "http://$SERVER_IP/docs"
echo ""
echo "Example API usage:"
echo "curl -X POST http://$SERVER_IP/run-crew/ \\"
echo "  -H \"X-API-Key: $API_KEY\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"crew_name\": \"my_research\", \"user_goal\": \"Research machine learning algorithms\"}'"
echo ""
echo "To check container logs:"
echo "docker logs research-crew-container"
echo ""
echo "To check Nginx logs:"
echo "tail -f /var/log/nginx/error.log"
echo "tail -f /var/log/nginx/access.log"
