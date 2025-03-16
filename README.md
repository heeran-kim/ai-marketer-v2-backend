# 🚀 Setting Up and Running a Git + Docker Project in WSL2

This guide provides step-by-step instructions to install **WSL2**, **Git**, and **Docker**, and how to run a project cloned from Git inside Docker.

---

## **🔹 Step 1: Enable WSL2**

### ✅ **1. Open PowerShell as Administrator**
Press `Win + X` → Click **PowerShell (Admin)** or **Terminal (Admin)**.

### ✅ **2. Install WSL2**
Run:
```sh
wsl --install
```
This installs **WSL2**, but does not install a Linux distribution yet.

### ✅ **3. Install a Linux Distribution**
Check available distributions:
```sh
wsl --list --online
```
Install a distribution (e.g., Ubuntu 22.04):
```sh
wsl --install -d Ubuntu-22.04
```
If you prefer another version, replace `Ubuntu-22.04` with your choice from the available list.

### ✅ **4. Check Installed WSL Versions (Run This in PowerShell, Not WSL)**
Run this **in PowerShell or Command Prompt (not inside WSL2):**
```sh
wsl --list --verbose
```
Expected output:
```
NAME            STATE           VERSION
Ubuntu-22.04    Running         2
```
If Ubuntu is using **WSL1**, change it to **WSL2**:
```sh
wsl --set-version Ubuntu-22.04 2
```

### ✅ **5. Open Ubuntu and Move to the Correct Directory**
Once WSL2 is installed, open Ubuntu from the Windows Start menu. If your prompt looks like this:
```sh
heeran@N53P105Z141418:/mnt/c/WINDOWS/system32$
```
You're inside WSL2 but navigating the Windows filesystem. Move to your WSL2 home directory:
```sh
cd ~
```
Your prompt should now look like:
```sh
heeran@N53P105Z141418:~$
```
✅ Now you are properly inside WSL2 (Ubuntu).

### ✅ **6. Restart WSL Instead of Restarting the Computer** (If Restart is Not Possible)
If you **cannot restart your computer**, manually restart WSL:
```sh
wsl --shutdown
wsl
```

---

## **🔹 Step 2: Install Git in WSL2**

Git is required to clone repositories. Run the following inside **WSL2 (Ubuntu):**
```sh
sudo apt update
sudo apt install git -y
```
Verify the installation:
```sh
git --version
```
If Git is installed successfully, you should see output like:
```
git version 2.34.1
```

To clone a Git repository, run:
```sh
git clone <repository-url>
cd <repository-name>
```

---

## **🔹 Step 3: Install Docker in WSL2 (Without Docker Desktop)**
If you do **not** have admin permissions to install Docker Desktop, install Docker directly inside WSL2.

Run the following inside **WSL2 (Ubuntu):**
```sh
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl gnupg
```
Add Docker’s official GPG key:
```sh
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo tee /etc/apt/keyrings/docker.asc > /dev/null
sudo chmod a+r /etc/apt/keyrings/docker.asc
```
Set up the Docker repository:
```sh
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```
Install Docker:
```sh
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```
Verify installation:
```sh
docker --version
```

---

## **🔹 Step 4: Create and Configure the `.env` File**
Since the `.env` file is not included in Git for security reasons, you must create it manually.

### ✅ **1. Use the `.env.example` File**
A sample `.env.example` file is included in the repository. Copy it to create your own `.env` file:
```sh
cp .env.example .env
```
Then open and edit the `.env` file:
```sh
nano .env
```
Fill in the required values based on your setup.

#### **Example `.env.example` File**:
```
DEBUG=False

POSTGRES_NAME=your-db-name
POSTGRES_USER=your-db-user
POSTGRES_PASSWORD=your-db-password
POSTGRES_HOST=db
POSTGRES_PORT=5432
USE_RENDER_DB=false
CORS_ALLOWED_ORIGINS=https://localhost:3000,https://your-frontend-url.com
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,your-frontend-url.com
```

### ✅ **2. Restart Docker to Load the `.env` File**
```sh
docker-compose down
docker-compose up --build -d
```
Or if using `docker run`:
```sh
docker stop <container_id>
docker run --env-file .env -d -p 8000:8000 my-app
```

---

## **🔹 Step 5: Set Up HTTPS in WSL2 with `mkcert`**
Run inside WSL2 (Ubuntu, inside your project directory):

### ✅ **1. Install `mkcert`**
```sh
sudo apt install libnss3-tools
wget -q https://github.com/FiloSottile/mkcert/releases/download/v1.4.4/mkcert-v1.4.4-linux-amd64 -O mkcert
chmod +x mkcert
sudo mv mkcert /usr/local/bin/
```
Run:
```sh
mkcert -install
```

### ✅ **2. Generate a Local SSL Certificate**
```sh
mkcert localhost
```
This creates:
```sh
localhost.pem (Certificate)
localhost-key.pem (Private Key)
```

---

## 🎯 **Done! Your Git + Docker + WSL2 setup is complete. 🚀**
Now you can run Linux-based containers **seamlessly inside Windows**.

If you need further automation, consider writing a setup script! 💻
