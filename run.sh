#!/bin/bash

# 必要なディレクトリがなければ作成
mkdir -p data
mkdir -p data/player_list
mkdir -p data/teams
mkdir -p log

if [ -f .env ]; then
  export $(cat .env | xargs)
fi

python bot.py > log/bot.log
