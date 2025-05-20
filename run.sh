#!/bin/bash

# 必要なディレクトリがなければ作成
mkdir -p /data/player_list
mkdir -p /data/teams

if [ -f .env ]; then
  export $(cat .env | xargs)
fi

nohup python3 bot.py > log/bot.log 2>&1 &
