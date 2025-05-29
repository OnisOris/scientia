# scientia
Automatically sort your knowledge

# Install (Ubuntu)

## Preinstall
Install docker
https://docs.docker.com/engine/install/ubuntu

install libpq-dev
```
sudo apt-get update && sudo apt-get install `libpq-dev`
```

## Project install

You have to rewrite settings for scientia in scientia_install.sh (in service) or in /home/$USER/scientia/.env

```
curl -o scientia_install.sh https://raw.githubusercontent.com/OnisOris/scientia/refs/heads/main/deployment/install.sh
chmod +x scientia_install.sh 
sudo ./scientia_install.sh 
```




