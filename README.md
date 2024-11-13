# Sistema de Pagamentos

Este é um sistema básico de pagamentos inspirado no PicPay, desenvolvido com **Python** e **Flask**. O sistema permite que usuários comuns enviem dinheiro entre si e para lojistas, enquanto lojistas apenas recebem pagamentos. 

## Funcionalidades do Projeto

- Cadastro de usuários e lojistas com validação de dados únicos (CPF/CNPJ e e-mail).
- Sistema de transferências entre usuários.
- Consulta de saldo antes de transferências.
- Validação de autorização de transferências com um serviço externo.
- Notificação de recebimento de pagamento com serviço de notificação externa.

## Estrutura do Projeto

Abaixo está a estrutura básica de diretórios do projeto:

sistema_pagamentos/
├── app/
│   ├── __init__.py         # Inicializador do aplicativo
│   ├── models.py           # Modelos do banco de dados
│   ├── routes.py           # Definição de rotas da API
│   ├── services.py         # Lógica de serviço para operações de pagamento
│   └── utils.py            # Funções utilitárias
├── venv/                   # Ambiente virtual (já criado)
├── requirements.txt        # Dependências do projeto
├── .gitignore              # Arquivos a serem ignorados pelo Git
└── README.md


## Instalação e Configuração

Para configurar e rodar o projeto em ambiente local, siga as instruções abaixo:

1. **Clone o Repositório**:
   ```bash
   git clone https://github.com/seu_usuario/sistema_pagamentos.git
   cd sistema_pagamentos

2. **Crie e Ative o Ambiente Virtual**:
    ```bash
    python -m venv venv
    # No Windows
    .\venv\Scripts\activate
    # No macOS/Linux
    source venv/bin/activate 

3. **Instale as Dependências**:
    ```bash
    pip install -r requirements.txt

4. **Execute o Servidor**:
    ```bash
    python run.py

Acesse http://127.0.0.1:5000/ no navegador para verificar se o servidor está rodando.

# Próximos Passos

- Implementação de rotas para operações de pagamento e saldo.
- Conexão com banco de dados e desenvolvimento dos modelos.
- Integração com serviços externos de autorização e notificação.

# Tecnologias Utilizadas

- Python 3.10+
- Flask
- Flask-SQLAlchemy - ORM para manipulação de banco de dados