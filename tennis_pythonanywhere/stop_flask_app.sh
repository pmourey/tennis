#!/bin/bash

PID=$(pgrep -f "flask run")

if [ "x$PID" != "x" ]; then
  for pid in $PID; do
    echo "PID: $pid"
    FLASK_RUN_PORT=$(lsof -i -P -n | grep LISTEN | grep $PID | awk '{print $9}' | cut -d: -f2)
    echo "A flask server is running on port $FLASK_RUN_PORT"
    echo "Do you really want to shutdown it? (Y/N)"
    # Lecture de l'entrée standard dans la variable 'input'
    while read -r input
    do
      case "$input" in
          "Y"|"y")
              echo "Fermeture du programme."
              kill "$PID"
              break
              ;;
          "N"|"n")
              echo "Annulation de la commande."
              break
              ;;
          *)
              echo "Invalid choice. Please enter [Y|y|N|n]."
              ;;
      esac
    done
  done
else
  echo "No flask server running on this computer!"
fi
