# GambleBot

### A new way to waste your time on the internet without entirely ruining your finances

<br>

## How to install

```bash
sudo apt install git python3 python3-pip python3-venv

cd /opt/
sudo git clone https://github.com/5Dev24/GambleBot
sudo chown -hR $(whoami) /opt/GambleBot/
cd /opt/GambleBot/

python3 -m venv ./venv/

source ./venv/bin/activate

pip3 install -r ./requirements.txt
```

<br>

## How to setup

```bash
# Replace "TOKEN" with your bot's secret token
echo "ClientSecret=TOKEN" > ./src/.env
```

<br>

## Running the bot

```bash
cd /opt/GambleBot/

source ./venv/bin/activate

python3 ./src/__main__.py
```

## Running the bot as a systemd service (on startup)

`/lib/systemd/system/GambleBot.service`
```
[Unit]
Description=GambleBot
After=network.target
StartLimitBurst=3
StartLimitIntervalSec=20

[Service]
ExecStart=/opt/GambleBot/venv/bin/python3 /opt/GambleBot/src/__main__.py
Restart=on-failure
RestartSec=3s

[Install]
WantedBy=multi-user.target
```

<br>

Then run these to enable it after adding the file to systemd
```bash
sudo systemctl enable GambleBot.service
sudo systemctl daemon-reload
sudo systemctl start GambleBot.service
```

## Congratulations

You've installed, setup, and ran the bot!

Welcome to years/months/weeks/days/hours/minutes/seconds of fun