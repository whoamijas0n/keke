#!/bin/bash
pkill -9 python3
pkill -9 xinit
pkill -9 Xorg
pkill -9 openbox
rm -rf /tmp/.X* /tmp/.x11-unix
sleep 2

#Iniciamos el servidor grafico 
startx /usr/bin/python3 /root/keke/keke_Raspberry.py
