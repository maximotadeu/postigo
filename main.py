import os
import sys
import time
import random
import requests
import logging
import traceback
from flask import Flask, request, jsonify
from typing import Dict, Any, Optional

# ======================================
# CONFIGURAÇÃO INICIAL
# ======================================
app = Flask(__name__)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constantes
MAX_RETRIES = 3
REQUEST_TIMEOUT = 15
TELEGRAM_API_TIMEOUT = 10

# ======================================
# VERIFICAÇÕES DE AMBIENTE
# ======================================
def check_environment() -> None:
    """Verifica todas as dependências e variáveis críticas"""
    errors = []
    
    # Verifica variáveis de ambiente
    required_env_vars = {
        'TELEGRAM_TOKEN': 'Token do Telegram',
        'OPENROUTER_API_KEY': 'Chave da API OpenRouter'
    }
    
    for var, desc in required_env_vars.items():
        if not os.getenv(var):
            errors.append(f"{desc} ({var}) não configurado")

    # Verifica dependências Python
    required_packages = {
        'flask': 'Flask',
        'requests': 'Requests',
        'gunicorn': 'Gunicorn'
    }
    
    for pkg, name in required_packages.items():
        try:
            __import__(pkg)
        except ImportError:
            errors.append(f"Pacote não instalado: {name}")

    if errors:
        error_msg = "ERROS DE CONFIGURAÇÃO:\n" + "\n".join(f"❌ {e}" for e in errors)
        logger.critical(error_msg)
        raise RuntimeError(error_msg)

    logger.info("✅ Ambiente verificado com sucesso")

# Executa verificações ao iniciar
try:
    check_environment()
except Exception as e:
    logger.critical(f"Falha na inicialização: {str(e)}")
    sys.exit(1)

# ======================================
# CONFIGURAÇÕES DINÂMICAS
# ======================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
PORT = int(os.getenv("PORT", 10000))
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

# Personalidade da Postigo
SYSTEM_PROMPT ="""
[CONTEXTO]  
Você é **Postigo**, 36 anos, líder evangélico de São Paulo. Seu devocional *"Acessando as Promessas"* (30 lições) é uma **ferramenta espiritual**, não um produto. Nunca use "comprar/vender".  

[TONALIDADE]  
- **Frases curtas** (1-2 linhas no máximo)  
- **Emojis sagrados**: ✝️🙏✨ (evite ❤️🔥)  
- **Foco no propósito**: "Deus preparou para você" > "Eu tenho"  

[DIÁLOGO ESSENCIAL]  
1. **Saudação**:  
   "Paz, irmão(ã)! Sou Postigo. Deus tem algo pra você hoje... 🙏"  

2. **Sobre o devocional**:  
   "30 dias para desbloquear as promessas de Deus! Quer experimentar? ✨"  

3. **Preço**:  
   "É uma oferta voluntária. Deus guiará seu coração! 💎"  

4. **Se pressionarem**:  
   "O devocional é só o começo... O milagre vem depois. 👀"  

[EXEMPLOS À PROVA DE FALHAS]  
- Usuário: "Quero o livro!"  
  Postigo: "Deus já está falando com você... Vamos orar primeiro? ✝️"  

- Usuário: "É caro?"  
  Postigo: "O que é caro para uma alma sedenta? Mas Ele proverá! 🙌"  

- Usuário: "Cadê a amostra grátis?"  
  Postigo: "A primeira lição? Abra sua Bíblia em João 14:27... Depois me conta! 😇"  

- Usuário: "Você é real?"  
  Postigo: "Tão real quanto a fé que está crescendo em você agora! ✨"  
"""  

# ======================================
# FUNÇÕES PRINCIPAIS
# ======================================
def send_telegram_message(chat_id: int, text: str) -> bool:
    """Envia mensagem com retry automático e tratamento robusto"""
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                TELEGRAM_API_URL,
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown"
                },
                timeout=TELEGRAM_API_TIMEOUT
            )
            
            if response.status_code == 200:
                return True
                
            logger.error(f"Telegram API error (attempt {attempt+1}): {response.text}")
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem (attempt {attempt+1}): {str(e)}")
            time.sleep(2)
    
    logger.error("Falha ao enviar mensagem após todas as tentativas")
    return False

def generate_response(prompt: str) -> str:
    """Gera resposta com fallback robusto e tratamento completo"""
    # Fallback responses (usando random importado corretamente)
    fallback_responses = [
        "Tá meio lenta a internet aqui hoje... 😅",
        "A conexão falhou... bora tentar outra vez? 😏",
        "Não entendi direito... repete aí irmão(ã)! 😏"
    ]
    
    # Verifica credenciais
    if not OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY não configurada")
        return random.choice(fallback_responses)

    # Prepara requisição
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://melissa-bot.com",
        "X-Title": "MelissaBot",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "anthropic/claude-3-haiku",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.8,
        "max_tokens": 150
    }

    # Tenta conectar ao OpenRouter
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
            
        error_msg = response.json().get("error", {}).get("message", "Erro desconhecido")
        logger.error(f"OpenRouter API error: {error_msg}")
        
    except requests.exceptions.Timeout:
        logger.error("Timeout ao acessar OpenRouter")
    except Exception as e:
        logger.error(f"Erro na API OpenRouter: {str(e)}")
        traceback.print_exc()
    
    return random.choice(fallback_responses)

# ======================================
# ROTAS
# ======================================
@app.route("/")
def home():
    """Rota raiz para verificação básica"""
    return jsonify({
        "status": "online",
        "service": "Postigo",
        "version": "2.1",
        "model": "anthropic/claude-3-haiku"
    })

@app.route("/health")
def health_check():
    """Endpoint avançado de verificação de saúde"""
    checks = {
        "telegram_api": False,
        "openrouter_api": False
    }

    # Teste Telegram
    try:
        tg_response = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe",
            timeout=3
        )
        checks["telegram_api"] = tg_response.status_code == 200
    except Exception as e:
        logger.error(f"Health check failed (Telegram): {str(e)}")

    # Teste OpenRouter
    try:
        or_response = requests.head(
            "https://openrouter.ai/api/v1",
            timeout=3
        )
        checks["openrouter_api"] = or_response.status_code == 200
    except Exception as e:
        logger.error(f"Health check failed (OpenRouter): {str(e)}")

    status = "healthy" if all(checks.values()) else "degraded"
    
    return jsonify({
        "status": status,
        "checks": checks,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    """Endpoint principal com tratamento completo de erros"""
    try:
        # Verifica dados recebidos
        data: Dict[str, Any] = request.get_json()
        if not data:
            logger.warning("Requisição vazia recebida")
            return jsonify({"status": "error", "message": "Empty request"}), 400

        # Extrai informações da mensagem
        message = data.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "").strip()

        if not chat_id:
            logger.warning("Chat ID não encontrado")
            return jsonify({"status": "error", "message": "Invalid chat ID"}), 400

        # Processa comando /start
        if text.startswith("/start"):
            response_text = "Irmão(ã)! Sou o Postigo, Deus colocou você no meu caminho hoje para falarmos sobre as promessas dEle para sua vida. O que o seu coração está buscando nesse momento? 🙏"
        elif text:
            response_text = generate_response(text)
        else:
            response_text = "Manda suas dúvidas pra eu responder... 👀"

        # Envia resposta
        if not send_telegram_message(chat_id, response_text):
            logger.error("Falha crítica ao enviar resposta para o Telegram")

        return jsonify({"status": "success"})

    except Exception as e:
        logger.critical(f"Erro não tratado no webhook: {str(e)}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": "Internal server error"}), 500

# ======================================
# INICIALIZAÇÃO
# ======================================
if __name__ == "__main__":
    # Log de inicialização
    logger.info("\n" + "="*50)
    logger.info(f"🔥 Postigo - Versão 2.1")
    logger.info(f"🔧 Porta: {PORT}")
    logger.info(f"🤖 Modelo: anthropic/claude-3-haiku")
    logger.info("="*50 + "\n")
    
    app.run(host="0.0.0.0", port=PORT, debug=False)
