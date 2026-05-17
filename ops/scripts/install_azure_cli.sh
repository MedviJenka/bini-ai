#!/bin/bash

curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
az login --use-device-code
az account show
