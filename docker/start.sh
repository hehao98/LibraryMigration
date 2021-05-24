#!/bin/bash

set -e

URL="http://127.0.0.1:8848"
DIR="../dbdata"

# create folder with user permission
if [[ ! -d $DIR ]]; then
    mkdir $DIR
fi

if [[ ! -w $DIR ]]; then 
    echo "You don't have write permissions to ${DIR}; MongoDB would exit on error"
    exit 1
fi

if [[ ! -x dbinit/mongodb_restore.sh ]]; then 
    chmod +x dbinit/mongodb_restore.sh
fi

# start container as current user
UID_GID="$(id -u):$(id -g)" docker-compose up --detach --build

# automatically open jupyter url on linux machine
[[ -x $BROWSER ]] && exec "$BROWSER" "$URL"
path=$(which xdg-open || which gnome-open) && exec "$path" "$URL"
echo "open jupyterlab in your browser: ${URL}"