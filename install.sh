#!/bin/bash

pip install -r requirements.txt

mkdir -p packages keys tmp
#ssh-keygen -t rsa -b 4096 -N "" -f keys/id_rsa