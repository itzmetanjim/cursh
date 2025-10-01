#!/bin/sh
echo "Installing cursh..."
wget -O cursh https://github.com/itzmetanjim/cursh/raw/refs/heads/main/exec/cursh
sudo chmod +x cursh
sudo cp ./cursh /usr/local/bin/
sudo chmod +x /usr/local/bin/cursh
echo "cursh installed to /usr/local/bin/cursh"