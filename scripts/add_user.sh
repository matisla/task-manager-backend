#!/bin/bash

baseurl="http://localhost:8000" 
username="matisla"

read -s -p 'password: ' password

http --form POST $baseurl/auth/register \
    username="$username" \
    password="$password" \
    email="$username@example.fr"
