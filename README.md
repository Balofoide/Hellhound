# HellHound - Port Connection Notifier

HellHound é um script Python que monitora tentativas de conexão e envia alertas em tempo real para um bot Telegram.

## Funcionalidades

- Monitora arquivo de log `/var/log/ssh_tunnel.log` em busca de conexões suspeitas.
- Envia notificações para um chat Telegram com detalhes do IP e localização geográfica.
- Atualiza o status do IP (online/offline) baseado no tempo desde a última conexão.

## Requisitos

- Python 3.8 ou superior
- Biblioteca python-telegram-bot
- Biblioteca geocoder

## Instalação

1. Clone o repositório ou copie o script para seu servidor.
2. Crie um Log na iptables com um Trigger para ativar o script.
3: Instale as dependências

```bash
pip install -r requirements.txt
