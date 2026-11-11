# 🚌 Análise da Frota de Ônibus de São Paulo

Projeto de análise de dados que coleta **automaticamente, a cada hora**, a quantidade de ônibus em circulação em cada linha da cidade de São Paulo, usando a API Olho Vivo da SPTrans.

Diferente de usar uma base pronta, aqui os dados são coletados e armazenados pelo próprio projeto, formando um histórico que cresce todos os dias.

## Perguntas que o projeto quer responder

- Em quais horários há mais ônibus rodando na cidade?
- Qual a diferença de frota entre dias úteis e fins de semana?
- Quais linhas têm mais e menos ônibus em circulação?

## Como funciona

1. O **GitHub Actions** executa o script `coleta.py` a cada hora.
2. O script se autentica na API, busca a posição de todos os ônibus e salva um resumo por linha.
3. O CSV atualizado é salvo de volta no repositório, aumentando o histórico.

## Tecnologias

- Python (requests, csv)
- API REST (Olho Vivo / SPTrans)
- GitHub Actions (automação agendada)

## Como rodar localmente

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    export SPTRANS_TOKEN="seu_token"
    python coleta.py

O token é gratuito e pode ser obtido na área de desenvolvedores do site da SPTrans.

## Autor

Deivid Azevedo Dantas — estudante de Análise e Desenvolvimento de Sistemas
