import asyncio
import logging
from logging.handlers import RotatingFileHandler
import subprocess
import time
from pathlib import Path
from telegram import Bot
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
PORTA = 8965
COOLDOWN = 10  
STATUS_TIMEOUT = 30  

LOG_FILE = Path('/var/log/ssh_tunnel.log')
POS_FILE = Path('/tmp/last_ssh_check.txt')
COOLDOWN_FILE = Path('/tmp/last_alert.txt')

LOG_TRIGGER = 'CONEXAO_SSH_TENTATIVA:'

for f in [LOG_FILE, POS_FILE, COOLDOWN_FILE]:
    f.touch(exist_ok=True)

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logger = logging.getLogger('HellHound')
bot = Bot(token=TOKEN)

targets = {}
locations = {}  

def file_ops(file, mode, data=None):
    try:
        with open(file, mode) as f:
            if 'w' in mode:
                return f.write(data)
            elif 'r' in mode:
                content = f.read()
                return int(content) if content.strip().isdigit() else 0
    except Exception as e:
        logger.error(f"Erro em {file}: {e}")
        return 0

def tunnel_active():
    try:
        result = subprocess.run(['ss', '-ltn'], capture_output=True, text=True, check=True)
        return f":{PORTA} " in result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Erro verificação túnel: {e}")
        return False

def extract_ip(line):
    for part in line.split():
        if part.startswith('SRC='):
            return part.split('=')[1]
    return 'IP Desconhecido'

def get_location(ip):
    if ip in locations:
        return locations[ip]
    try:
        city = geocoder.ip(ip).city
        if not city:
            city = "Desconhecido"
    except Exception:
        city = "Desconhecido"
    locations[ip] = city
    return city

async def notify_target(ip):
    now = time.time()

    if ip in targets:
        if not targets[ip].get("active", True):
            targets[ip]["active"] = True
            targets[ip]["count"] = 1
        else:
            targets[ip]["count"] += 1
        targets[ip]["last_seen"] = now

        try:
            await bot.delete_message(chat_id=CHAT_ID, message_id=targets[ip]["message_id"])
        except Exception as e:
            logger.error(f"Erro ao deletar mensagem antiga para {ip}: {e}")
    else:
        targets[ip] = {
            "count": 1,
            "last_seen": now,
            "active": True
        }

    dt = datetime.fromtimestamp(targets[ip]["last_seen"])
    data_formatada = dt.strftime("%d/%m/%Y")
    hora_formatada = dt.strftime("%H:%M:%S")

    location = get_location(ip)

    msg = await bot.send_message(
        chat_id=CHAT_ID,
        text=(
            f"🚨 HellHound Alert!\n"
            f"📡 IP: {ip}\n"
            f"📍 Location: {location}\n"
            f"⏰ Last Ping:{hora_formatada}\n{data_formatada}\n"
            f"🔄 HeartBeat: {targets[ip]['count']}\n"
            f"🟢 Status: Online"
        ),
        parse_mode=ParseMode.HTML
    )
    targets[ip]["message_id"] = msg.message_id

async def check_targets_status():
    while True:
        now = time.time()
        for ip, data in list(targets.items()):
            elapsed = now - data["last_seen"]

            if data.get("active", True) and elapsed > STATUS_TIMEOUT:
                data["active"] = False

                dt = datetime.fromtimestamp(data["last_seen"])
                data_formatada = dt.strftime("%d/%m/%Y")
                hora_formatada = dt.strftime("%H:%M:%S")

                location = get_location(ip)

                text = (
                    f"🚨 HellHound Alert!\n"
                    f"📡 IP: {ip}\n"
                    f"📍 Location: {location}\n"
                    f"⏰ Last Ping:{hora_formatada}\n{data_formatada}\n"
                    f"🔄 HeartBeat: {data['count']}\n"
                    f"🔴 Status: Offline"
                )g
                try:
                    await bot.edit_message_text(
                        chat_id=CHAT_ID,
                        message_id=data["message_id"],
                        text=text,
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    logger.error(f"Erro ao marcar inativo para {ip}: {e}")
        await asyncio.sleep(10)

async def clear_log_file():
    while True:
        try:
            with open(LOG_FILE, 'w') as f:
                f.truncate(0)
            logger.info("Arquivo de log limpo.")
        except Exception as e:
            logger.error(f"Erro ao limpar o arquivo de log: {e}")
        await asyncio.sleep(600)

async def monitor():
    last_pos = file_ops(POS_FILE, 'r')
    logger.info(f"Última posição lida: {last_pos}")
    try:
        if LOG_FILE.stat().st_size < last_pos:
            logger.warning("Arquivo de log foi truncado. Redefinindo posição para o início.")
            last_pos = 0
            file_ops(POS_FILE, 'w', str(last_pos))

        with open(LOG_FILE, 'r') as f:
            f.seek(last_pos)
            lines = f.readlines()
            if lines:
                file_ops(POS_FILE, 'w', str(f.tell()))
                logger.info(f"Novas linhas detectadas: {len(lines)}")
                if not tunnel_active() and (time.time() - os.path.getmtime(COOLDOWN_FILE)) > COOLDOWN:
                    for line in lines:
                        if LOG_TRIGGER in line:
                            ip = extract_ip(line)
                            await notify_target(ip)
                            COOLDOWN_FILE.touch()
                            break
    except Exception as e:
        logger.error(f"Erro no monitoramento: {e}")

async def main():
    await bot.send_message(chat_id=CHAT_ID, text="🐾 HellHound Ativado!")
    logger.info("Serviço Iniciado")

    asyncio.create_task(clear_log_file())
    asyncio.create_task(check_targets_status())

    try:
        while True:
            await monitor()
            await asyncio.sleep(10)
    except (KeyboardInterrupt, Exception) as e:
        logger.info(f"Serviço Interrompido: {e}")

if __name__ == '__main__':
    asyncio.run(main())
