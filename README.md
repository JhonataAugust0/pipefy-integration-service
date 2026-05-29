# Mundo Invest — Backend Challenge: Pipefy Integration Service

> **Stack:** Python 3.14 · FastAPI · SQLAlchemy · PostgreSQL · Pytest · Docker   
>![Quality Gate](assets/quality_gate.svg) 
![Maintainability A](assets/maintainability.svg)
![Security Rating A](assets/security_rating.svg)
![Duplicated Lines](assets/duplicated_lines.svg)
---

## Sumário

1. [Visão de Produto e Negócio](#1-visão-de-produto-e-negócio)
2. [Arquitetura de Software e Infraestrutura Local](#2-arquitetura-de-software-e-infraestrutura-local)
   - [2.4 Mapeamento GraphQL — Mutations do Pipefy](#24-mapeamento-graphql--mutations-do-pipefy)
3. [Visão de Produção (AWS)](#3-visão-de-produção-aws)
4. [Plano de Execução](#4-plano-de-execução)
5. [Como Executar Localmente](#5-como-executar-localmente)
6. [Exemplos de Requisição](#6-exemplos-de-requisição)

---

## 1. Visão de Produto e Negócio

### 1.1 Personas

| Persona | Descrição | Interesse primário |
|---|---|---|
| **Operador Mundo Invest** | Analista interno que usa o Pipefy para gerenciar o ciclo de vida de clientes. Não interage com a API diretamente — suas ações no Pipefy disparam eventos. | Ter os dados de cliente e prioridade refletidos em tempo real, sem duplicidades. |
| **Sistema Pipefy** | Ator externo (BPM SaaS) que envia webhooks ao sistema sempre que um card é atualizado. Não é confiável por natureza: pode reenviar o mesmo evento em caso de timeout ou falha de entrega. | Receber confirmação de processamento (HTTP 200) para não re-disparar o evento indefinidamente. |
| **Desenvolvedor / Time de Engenharia** | Responsável por manter a integridade da integração, evoluir as mutations GraphQL e garantir cobertura de testes. | Código isolado e testável, sem acoplamento direto ao Pipefy em ambiente local. |

---

### 1.2 Requisitos Funcionais

| ID | Descrição |
|---|---|
| **RF-01** | A API deve expor o endpoint `POST /clientes` para criação de clientes. |
| **RF-02** | O endpoint `POST /clientes` deve validar presença dos campos obrigatórios (`cliente_nome`, `cliente_email`, `tipo_solicitacao`, `valor_patrimonio`) e formato de e-mail. |
| **RF-03** | Um cliente criado deve ser persistido no banco de dados com status inicial `"Aguardando Análise"`. |
| **RF-04** | Na criação, o sistema deve estruturar e registrar a mutation GraphQL `createCard` com as variáveis do cliente (nome, e-mail, patrimônio), seguindo a especificação oficial do Pipefy. |
| **RF-05** | A API deve expor o endpoint `POST /webhooks/pipefy/card-updated` para receber notificações de atualização de card. |
| **RF-06** | O endpoint de webhook deve verificar o `event_id` e ignorar (sem processar) qualquer evento já processado anteriormente (controle de idempotência). |
| **RF-07** | O endpoint de webhook deve buscar o cliente pelo `cliente_email` e retornar erro se não encontrado. |
| **RF-08** | Se `valor_patrimonio >= 200.000`, o sistema deve definir a prioridade como `prioridade_alta`; caso contrário, `prioridade_normal`. |
| **RF-09** | O status do cliente deve ser atualizado para `"Processado"` e a prioridade calculada persistida no banco. |
| **RF-10** | O sistema deve estruturar e registrar a mutation GraphQL `updateCardField` com o novo status e a prioridade calculada, seguindo a especificação oficial do Pipefy. |

---

### 1.3 Histórias de Usuário

#### US-01 · Criação de Cliente

> **Como** Operador Mundo Invest,  
> **Eu quero** registrar um novo cliente com nome, e-mail, tipo de solicitação e patrimônio via API,  
> **Para que** o cliente seja persistido no banco com status inicial rastreável e o payload de criação de card no Pipefy seja estruturado e auditável.

#### US-02 · Processamento de Webhook de Atualização

> **Como** Sistema Pipefy,  
> **Eu quero** notificar o sistema interno quando um card for atualizado, enviando `event_id`, `card_id`, `cliente_email` e `timestamp`,  
> **Para que** o sistema calcule a prioridade do cliente com base no patrimônio, atualize seu status no banco e estruture o payload de update GraphQL para o Pipefy — sem processar o mesmo evento duas vezes.

---

### 1.4 Critérios de Aceite (BDD)

#### US-01 · Criação de Cliente

```
Scenario: Criação de cliente com payload válido
  Given um payload com "cliente_nome", "cliente_email" válido, "tipo_solicitacao" e "valor_patrimonio"
  When uma requisição POST é enviada para /clientes
  Then o sistema retorna HTTP 201
  And o cliente é persistido no banco com status "Aguardando Análise"
  And a mutation GraphQL "createCard" é estruturada com nome, e-mail e patrimônio como variáveis

Scenario: Criação de cliente com e-mail inválido
  Given um payload onde "cliente_email" não é um endereço de e-mail válido
  When uma requisição POST é enviada para /clientes
  Then o sistema retorna HTTP 422 com mensagem de erro descritiva
  And nenhum registro é persistido no banco

Scenario: Criação de cliente com campo obrigatório ausente
  Given um payload sem o campo "cliente_nome"
  When uma requisição POST é enviada para /clientes
  Then o sistema retorna HTTP 422
  And nenhum registro é persistido no banco
```

#### US-02 · Processamento de Webhook

```
Scenario: Webhook com patrimônio >= 200.000 (prioridade alta)
  Given um cliente existente no banco com "valor_patrimonio" = 250000
  And um payload de webhook com "event_id" inédito e "cliente_email" correspondente
  When uma requisição POST é enviada para /webhooks/pipefy/card-updated
  Then o sistema retorna HTTP 200
  And o status do cliente é atualizado para "Processado"
  And a prioridade definida é "prioridade_alta"
  And a mutation GraphQL "updateCardField" é estruturada com status "Processado" e prioridade "prioridade_alta"
  And o "event_id" é registrado na tabela de eventos processados

Scenario: Webhook com patrimônio < 200.000 (prioridade normal)
  Given um cliente existente no banco com "valor_patrimonio" = 150000
  And um payload de webhook com "event_id" inédito e "cliente_email" correspondente
  When uma requisição POST é enviada para /webhooks/pipefy/card-updated
  Then o sistema retorna HTTP 200
  And a prioridade definida é "prioridade_normal"

Scenario: Bloqueio de idempotência por event_id duplicado
  Given um "event_id" = "evt_123" que já foi processado com sucesso
  When uma requisição POST é enviada para /webhooks/pipefy/card-updated com o mesmo "event_id"
  Then o sistema retorna HTTP 200 (resposta idempotente, não erro)
  And nenhuma escrita é realizada no banco
  And nenhuma mutation GraphQL é estruturada

Scenario: Webhook para cliente inexistente
  Given um payload com "cliente_email" que não existe no banco
  When uma requisição POST é enviada para /webhooks/pipefy/card-updated
  Then o sistema retorna HTTP 404
  And nenhuma escrita é realizada
```

---

## 2. Arquitetura de Software e Infraestrutura Local

### 2.1 Justificativa da Stack

| Tecnologia | Justificativa |
|---|---|
| **Python 3.14** | Requisito do desafio (Python ou Golang); ecossistema maduro para integrações com APIs externas e automações. |
| **FastAPI** | Validação automática via Pydantic, geração de OpenAPI out-of-the-box e performance assíncrona adequada para I/O-bound workloads como chamadas GraphQL. |
| **Pydantic Settings** | Centraliza a leitura e tipagem de variáveis de ambiente (`.env`), garantindo *fail-fast* no startup da aplicação caso dependências vitais (como `DATABASE_URL`) estejam ausentes. |
| **SQLAlchemy 2.x** | ORM com suporte nativo a async; desacopla a camada de dados do banco físico, facilitando migrations e testes contra PostgreSQL real via instância dedicada no Docker Compose. |
| **PostgreSQL (Docker)** | Banco relacional usado tanto em desenvolvimento quanto em testes² (via `db-test`), espelhando o ambiente de produção (RDS) e garantindo que `ON CONFLICT`, constraints e tipos se comportem identicamente em todos os ambientes. |
| **Alembic** | Migrações versionadas; essencial para rastrear mudanças de schema sem recriar o banco. |
| **Pytest + pytest-asyncio** | Padrão de mercado para Python; suporte nativo a fixtures assíncronas contra PostgreSQL real (`db-test` no Docker Compose), garantindo paridade de comportamento com produção. |
| **Docker Compose** | Garante paridade entre ambientes de desenvolvimento, permite a reprodução fácil dos ambientes. |

> **Por que FastAPI?** Para um serviço que atua como consumidor de webhooks e orquestrador de chamadas GraphQL (I/O-bound workloads), o FastAPI é a ferramenta ideal. Enquanto frameworks síncronos como Flask bloqueiam a thread de execução aguardando a resposta do banco ou do Pipefy, o motor assíncrono do FastAPI libera o event loop para aceitar webhooks concorrentes sem exaurir recursos¹. Além disso, a validação de contratos estritos em integrações entre sistemas é um ponto de falha comum; o Pydantic nativo garante que payloads malformados do Pipefy sejam rejeitados na camada HTTP — com mensagens de erro claras — antes mesmo de tocarem a regra de negócio.

---

### 2.2 Infraestrutura Local (Docker Compose)

```
┌─────────────────────────────────────────────┐
│              docker-compose.yml             │
│                                             │
│  ┌──────────────┐      ┌──────────────────┐ │
│  │  api         │────▶│  db (postgres)   │ │
│  │  FastAPI:8000│      │  postgres:5432   │ │
│  │  volume: .   │      │  volume: pgdata  │ │
│  └──────────────┘      └──────────────────┘ │
└─────────────────────────────────────────────┘
```

- O serviço `api` monta o diretório local como volume para hot-reload via `uvicorn --reload`.
- O serviço `db` usa um volume nomeado (`pgdata`) para persistência entre restarts.
- As variáveis de conexão são injetadas via `.env`.
- O healthcheck no `db` garante que a API só sobe após o PostgreSQL aceitar conexões.

---

### 2.3 Padrão Arquitetural

A aplicação segue uma **Arquitetura em Camadas** com inspiração hexagonal (Ports & Adapters), simplificada ao nível de complexidade do desafio:

```
app/
├── api/                   # Camada de Transporte (FastAPI Routers)
│   ├── v1/
│   │   ├── clientes.py    # POST /clientes
|   |   ├── system.py      # GET /health
│   │   └── webhooks.py    # POST /webhooks/pipefy/card-updated
|   ├── deps.py            # Injeção de dependências
│   └── error_handler.py   # Handler global de exceções
|
├── core/                  # Configurações Centrais
│   └── settings.py        # Gerenciamento de variáveis de ambiente
|
├── db/
│   └── session.py         # Engine e SessionLocal
|
├── domain/                # Regras de Negócio Puras
|   ├── exceptions.py      # Exceções de Domínio
│   └── priority.py        # Função: calculate_priority(asset_value: float) → str
|
├── integrations/          # Adapters Externos (Ports)
│   └── pipefy/
│       ├── client.py      # Simulação do cliente GraphQL (mock/stub)
│       └── mutations.py   # Strings das mutations GraphQL (createCard, updateCardField)
│
├── models/                # Modelos SQLAlchemy (ORM)
│   ├── cliente.py         # Tabela de registro de clientes
│   └── processed_event.py # Tabela de processamento de eventos
│
├── schemas/               # Modelos Pydantic (I/O da API)
│   ├── cliente.py
│   └── webhook.py
|
├── services/              # Camada de Aplicação (Casos de Uso)
│   ├── cliente_service.py # Orquestra validação, persistência e chamada ao Pipefy client
│   └── webhook_service.py # Orquestra idempotência, regra de prioridade e update
│
└── main.py                # Instância FastAPI, inclusão de routers
```

**Princípios aplicados:**

- Os `services` nunca importam de `api/`; os `routers` nunca contêm regras de negócio.
- A camada `domain/` é pura Python, sem dependências de framework.
- O `pipefy/client.py` recebe a mutation pronta e simula o envio; em produção, seria substituído por uma chamada `httpx` real sem alterar nenhuma outra camada.
- A tabela `processed_event` garante idempotência no banco antes de qualquer escrita de negócio.

---

## 2.4 Mapeamento GraphQL — Mutations do Pipefy

As duas mutations abaixo são o contrato entre este sistema e o Pipefy. Estão implementadas em `integrations/pipefy/mutations.py` seguindo rigorosamente a [documentação oficial do Pipefy](https://developers.pipefy.com/reference/mutations). O `pipefy_client.py` recebe a string da mutation e as variáveis preenchidas pelo service, simulando localmente o envio real.

---

### `createCard` — Disparada em `POST /clientes`

Cria um novo card no pipe correspondente ao cliente recém-cadastrado.

**Query:**

```graphql
mutation createCard($input: CreateCardInput!) {
  createCard(input: $input) {
    card {
      id
      title
      createdAt
      url
      uuid
      done
      late
      expired
      due_date
      started_current_phase_at
      current_phase_age
      creatorEmail
      emailMessagingAddress
      inboxEmailsRead
      attachments_count
      comments_count
      checklist_items_count
      checklist_items_checked_count
      public_form_submitter_email
      age
      overdue
      finished_at
      updated_at
      path
      suid
    }
  }
}
```

**Variáveis preenchidas pelo `cliente_service.py`:**

```json
{
  "input": {
    "pipe_id": "<PIPE_ID>",
    "title": "<cliente_nome>",
    "fields_attributes": [
      { "field_id": "email",      "field_value": "<cliente_email>" },
      { "field_id": "patrimonio", "field_value": "<valor_patrimonio>" },
      { "field_id": "tipo",       "field_value": "<tipo_solicitacao>" }
    ],
    "phase_id": "<PHASE_ID_AGUARDANDO_ANALISE>"
  }
}
```

> **Nota de implementação:** `pipe_id` e `phase_id` são lidos de variáveis de ambiente (`PIPEFY_PIPE_ID`, `PIPEFY_PHASE_ID`). Os `field_id`s acima são placeholders — os valores reais dependem da configuração do pipe no Pipefy do Mundo Invest e seriam obtidos via query `pipe(id: ...)` na API.

---

### `updateCardField` — Disparada em `POST /webhooks/pipefy/card-updated`

Atualiza os campos de status e prioridade de um card existente após o processamento do webhook.

`updateCardField` aceita um campo por chamada. Para atualizar `status` e `prioridade` em uma **única requisição HTTP**, o service usa *aliasing* GraphQL: duas mutations são declaradas no mesmo documento com aliases distintos. A especificação GraphQL garante execução **sequencial e em ordem** para múltiplas mutations em um mesmo documento, ao contrário de queries, que podem ser paralelizadas.

**Query com aliasing:**

```graphql
mutation updateCardFields(
  $inputStatus:    UpdateCardFieldInput!,
  $inputPrioridade: UpdateCardFieldInput!
) {
  updateStatus: updateCardField(input: $inputStatus) {
    clientMutationId
    success
  }
  updatePrioridade: updateCardField(input: $inputPrioridade) {
    clientMutationId
    success
  }
}
```

**Variáveis preenchidas pelo `webhook_service.py`:**

```json
{
  "inputStatus": {
    "card_id": "<card_id>",
    "field_id": "status",
    "new_value": ["Processado"]
  },
  "inputPrioridade": {
    "card_id": "<card_id>",
    "field_id": "prioridade",
    "new_value": ["prioridade_alta"]
  }
}
```

A lógica que determina `new_value` para o campo `prioridade` vive em `domain/priority.py`:

```python
HIGH_PRIORITY_THRESHOLD = 200_000

def calculate_priority(asset_value: float) -> str:
    """Calculates customer priority based on invested assets."""
    if asset_value >= HIGH_PRIORITY_THRESHOLD:
        return "prioridade_alta"
    return "prioridade_normal"
```


---

### 2.5 Limitações Conhecidas e Escopo Deliberado

| # | Limitação | Impacto | Mitigação futura |
|---|---|---|---|
| L-01 | `pipefy_card_id` é persistido no modelo `Cliente` mas não exposto na resposta do `POST /clientes` (o Pipefy mock retorna um ID simulado). | Em produção, a resposta deveria retornar o `card_id` real para rastreabilidade. | Conectar o `pipefy_client` à API real e incluir `pipefy_card_id` no schema de resposta. |
| L-02 | O sistema só atualiza o card no Pipefy no contexto reativo de um webhook. Não há endpoint para acionar `updateCardField` de forma proativa. | Sem o `card_id` vindo do webhook, uma chamada proativa exigiria buscar o `pipefy_card_id` do banco — campo disponível, fluxo não implementado. | Implementar `PATCH /clientes/{id}/sync-pipefy` que lê `pipefy_card_id` do banco e dispara `updateCardField`. |
| L-03 | `updateCardField` com aliasing GraphQL não é atômico do ponto de vista do Pipefy: se `updateStatus` for bem-sucedido e `updatePrioridade` falhar, o card ficará em estado parcialmente atualizado. | Inconsistência de dados no Pipefy — o banco local estará correto, o Pipefy não. | Tratar `success: false` em qualquer alias como falha total; logar para reprocessamento. Avaliar a mutation `updateCard` com `fields_attributes` em array como alternativa single-call. |

## 3. Visão de Produção (AWS)

### 3.1 Visão Geral da Arquitetura

```
Pipefy Webhook
      │
      ▼
┌─────────────────┐
│  API Gateway    │  ← Throttling, autenticação por API Key/HMAC signature
│  (HTTP API)     │
└────────┬────────┘
         │ Enfileira sem processar (resposta imediata HTTP 200)
         ▼
┌─────────────────┐
│   Amazon SQS    │  ← Standard Queue com DLQ (Dead Letter Queue) para falhas
│  (card-updated) │    Visibility timeout: 30s | Max receives: 3
└────────┬────────┘
         │ Trigger (batch size: 1)
         ▼
┌─────────────────────────────────────────────────────────┐
│               AWS Lambda (webhook-processor)             │
│                                                          │
│  1. Extrai event_id do payload SQS                       │
│  2. Inicia transação no RDS (via RDS Proxy)              │
│  3. INSERT INTO processed_events (event_id)              │
│     ON CONFLICT DO NOTHING → se 0 rows: já processado,  │
│     faz rollback e retorna (ack para SQS)                │
│  4. Busca cliente pelo cliente_email                     │
│  5. Calcula prioridade (patrimônio >= 200k)              │
│  6. Atualiza status/prioridade do cliente                │
│  7. Estrutura e envia mutation updateCardField ao Pipefy │
│  8. COMMIT (idempotência + negócio = 1 transação)        │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  Amazon RDS     │
│  PostgreSQL     │
│  (Multi-AZ)     │
│  processed_events│
│  + clientes     │
└─────────────────┘
```

### 3.2 Fluxo Resiliente do Webhook — Análise Detalhada

**Por que não processar diretamente no Lambda via API Gateway?**

Webhooks do Pipefy podem ser reenviados se não receberem HTTP 200 em tempo hábil. Processar sincronicamente (validar → acessar banco → enviar resposta) expõe o sistema a timeouts se o RDS estiver sob carga. A solução é desacoplar recebimento de processamento:

1. **API Gateway** recebe o POST, valida o formato mínimo do payload e enfileira na SQS. Responde HTTP 200 em < 50ms. O Pipefy considera o evento entregue.

2. **SQS** absorve picos de carga. Se 1.000 webhooks chegarem simultaneamente, eles aguardam na fila sem sobrecarregar o banco. O `visibility timeout` (30s) garante que, se o Lambda falhar, o evento volta à fila para nova tentativa.

3. **Dead Letter Queue (DLQ):** Após 3 falhas consecutivas, o evento vai para a DLQ. Um alarme CloudWatch monitora o DLQ e aciona o time via SNS. Isso evita perda silenciosa de eventos.

4. **Lambda** processa com `batch_size=1` para garantir que uma falha em um evento não contamine o batch. O Lambda tem acesso ao RDS via **RDS Proxy**, que mantém um pool de conexões quentes — Lambda functions são stateless e abrir uma nova conexão TCP ao banco a cada invocação destrói a performance.

5. **Idempotência transacional no RDS:** A tabela `processed_events` vive no mesmo PostgreSQL dos dados de negócio. O Lambda executa `INSERT INTO processed_events (event_id) ON CONFLICT DO NOTHING` e verifica o número de linhas afetadas — se zero, o evento já foi processado e o Lambda retorna imediatamente sem escrita. Se inseriu, prossegue com o update do cliente. **Ambas as operações estão na mesma transação:** se o update falhar, o `INSERT` na `processed_events` também é revertido, e o evento voltará da SQS para nova tentativa em estado limpo. Não há transação distribuída; não há inconsistência.

### 3.3 Banco de Dados

**Decisão: Amazon RDS PostgreSQL (Multi-AZ) para tudo.**

A tabela `processed_events` vive no mesmo banco dos dados de negócio. Isso não é descuido de arquitetura — é a decisão correta para este volume de carga (BPM corporativo, não streaming de eventos). O motivo é direto: não existe transação atômica entre DynamoDB e PostgreSQL. Separar o controle de idempotência em um banco distinto introduz o problema clássico de transação distribuída — se o update no RDS falha após o write no DynamoDB, o evento fica marcado como processado incorretamente e nunca será reprocessado. O DynamoDB só seria justificável aqui se o volume de webhooks fosse da ordem de dezenas de milhares por segundo, criando contenção real na tabela `processed_events`. Para um BPM como o Pipefy, isso não acontece.

| Componente | Serviço | Justificativa |
|---|---|---|
| Dados de clientes | RDS PostgreSQL Multi-AZ | Modelo relacional, queries por e-mail, failover automático |
| Idempotência (`processed_events`) | RDS PostgreSQL (mesma instância) | Transação atômica com os dados de negócio, sem overhead de consistência distribuída |
| Connection pooling | RDS Proxy | Lambda sem pool fixo abre nova conexão TCP por invocação; destrói performance e ultrapassa `max_connections` do RDS sob carga |

### 3.4 Considerações de Segurança

- API Gateway valida a assinatura HMAC do webhook do Pipefy (`X-Pipefy-Signature`) antes de enfileirar, bloqueando requisições forjadas.
- Lambda acessa o RDS via IAM Role (sem credenciais hardcodadas). Secrets de banco gerenciados via AWS Secrets Manager.
- RDS em subnet privada, sem acesso público. Lambda na mesma VPC, acesso via Security Group.

---

### 3.5 Resiliência de Rede e Prevenção de Transaction Pinning

Uma armadilha comum em arquiteturas Serverless que integram bancos relacionais com APIs externas é o esgotamento do pool de conexões derivado de latência de rede. 

Embora o **RDS Proxy** atue como um multiplexador vital, ele obedece à regra de *Transaction Pinning*³: no exato momento em que o Lambda abre a transação local para garantir a idempotência e o estado da regra de negócio, o RDS Proxy fixa uma conexão física do PostgreSQL exclusivamente para aquele Lambda. 

Se a API do Pipefy enfrentar instabilidade e a requisição HTTP (mutation GraphQL) ficar retida por longos períodos, a conexão com o banco ficará refém dessa espera. Sob um pico de webhooks simultâneos, isso esgotaria o limite de conexões (`max_connections`) do PostgreSQL, causando um colapso na aplicação por inanição (*Starvation*).

**Mitigação Arquitetural (Fail-Fast):**
Para blindar o banco de dados contra instabilidades de terceiros, a arquitetura implementa o padrão *Fail-Fast* na camada de rede:
1. **Timeout Agressivo:** O cliente HTTP que consome o Pipefy possui um timeout estrito (ex: 5.0 segundos). O código não confia na latência de sistemas externos enquanto segura transações de banco.
2. **Rollback Imediato:** Em caso de *timeout*, a transação no RDS sofre um `ROLLBACK` instantâneo. A conexão física é imediatamente devolvida ao pool do RDS Proxy para ser usada por outros processos saudáveis.
3. **Delegação de Retentativa:** O Lambda falha intencionalmente e de forma limpa. Como a mensagem do webhook original está protegida no **Amazon SQS**, a própria infraestrutura da AWS se encarrega de reentregar o evento nos próximos minutos, aguardando que a API do Pipefy tenha estabilizado.

---

## 4. Plano de Execução

O desafio é decomposto em cinco etapas sequenciais. Cada etapa produz código funcional e testável antes de avançar.

### Etapa 1 · Setup e Modelagem (base)

- Inicializar repositório com estrutura de pastas descrita na seção 2.3.
- Configurar `docker-compose.yml` com serviços `api` e `db`.
- Definir modelos SQLAlchemy: `Cliente` (nome, email, tipo_solicitacao, valor_patrimonio, status, prioridade, `pipefy_card_id: Optional[str]`) e `ProcessedEvent` (event_id, processed_at). O campo `pipefy_card_id` é preenchido com o `id` retornado pelo `createCard` e usado pelo `webhook_service` para montar o `updateCardField`.
- Criar primeira migração Alembic e validar que as tabelas sobem corretamente.
- Configurar `pytest` com fixture que aponta para o serviço `db-test` (PostgreSQL 16, porta 5433) via `TEST_DATABASE_URL`. Banco de testes usa `tmpfs` (sem volume persistido) — cada run parte de estado limpo, garantindo que `ON CONFLICT DO NOTHING` e constraints se comportem exatamente como no RDS.

**Critério de saída:** `docker-compose up` sobe sem erros; `pytest` roda zero testes com zero falhas.

### Etapa 2 · Pipefy Client (Mock)

- Criar `integrations/pipefy/mutations.py` com as strings das mutations GraphQL (`createCard`, `updateCardField`) seguindo rigorosamente a documentação oficial do Pipefy.
- Criar `integrations/pipefy/client.py` com função `send_mutation(mutation: str, variables: dict) -> dict` que loga o payload e retorna uma resposta simulada.
- Escrever um teste unitário que valida que a mutation `createCard` contém as variáveis `name`, `email` e `patrimônio`.

**Critério de saída:** Teste do client passa; as strings GraphQL são rastreáveis e revisáveis isoladamente.

### Etapa 3 · Fluxo 1: Criação de Cliente

- Implementar schema Pydantic `ClienteCreate` com validação de e-mail (EmailStr) e campos obrigatórios.
- Implementar `cliente_service.py`: validar → persistir com status `"Aguardando Análise"` → chamar `pipefy_client.send_mutation`.
- Implementar router `POST /clientes`.
- Escrever testes: (a) criação com payload válido verifica persistência e status; (b) payload com e-mail inválido retorna 422; (c) payload incompleto retorna 422.

**Critério de saída:** 3 testes passando; endpoint funcional via `curl`.

### Etapa 4 · Fluxo 2: Webhook e Idempotência

- Implementar schema Pydantic `WebhookPayload` (event_id, card_id, cliente_email, timestamp).
- Implementar `domain/priority.py`: `calcular_prioridade(valor: float) -> str`.
- Implementar `webhook_service.py`:
  1. Abrir transação no banco.
  2. `INSERT INTO processed_events (event_id) ON CONFLICT DO NOTHING` — se `rowcount == 0`, fazer rollback e retornar resposta idempotente (HTTP 200, `idempotent: true`).
  3. Buscar cliente por `cliente_email` → retornar 404 se não existir (rollback implícito).
  4. Calcular prioridade via `domain/priority.py`.
  5. Atualizar `status` e `prioridade` do cliente.
  6. Chamar `pipefy_client.send_mutation` com `updateCardField`.
  7. COMMIT — idempotência e negócio em uma única transação atômica.
- Implementar router `POST /webhooks/pipefy/card-updated`.
- Escrever testes: (a) patrimônio >= 200k → `prioridade_alta`; (b) patrimônio < 200k → `prioridade_normal`; (c) `event_id` duplicado → 200 sem escrita.

**Critério de saída:** 3 testes obrigatórios do desafio passando; idempotência validada com chamada dupla ao endpoint.

### Etapa 5 · Testes, Documentação e Revisão Final

- Revisar cobertura de testes: garantir que `domain/priority.py` e os services têm cobertura de casos de borda (patrimônio exatamente em 200.000, e-mail inexistente no webhook).
- Finalizar `README.md` com instruções de execução e exemplos `curl`.
- Executar `docker-compose up` em ambiente limpo e validar os dois fluxos end-to-end.
- Preparar roteiro do vídeo de defesa (7 min): background → estrutura de pastas → mutations GraphQL → testes no terminal → endpoints ao vivo.

**Critério de saída:** `pytest -v` mostra todos os testes em verde; endpoints respondem corretamente em ambiente Docker limpo.

---

## 5. Como Executar Localmente

### Pré-requisitos

- Docker e Docker Compose instalados.
- Arquivo `.env` na raiz (copiar de `.env.example`).

### Subir a aplicação (Com Docker)

```bash
# Clonar o repositório
git clone https://github.com/JhonataAugust0/pipefy-integration-service.git && cd pipefy-integration-service

# Copiar variáveis de ambiente
cp env.example .env

# Subir banco e API
docker-compose up --build

# Em outro terminal: rodar migrações
docker-compose exec api alembic upgrade head
```

### Subir a aplicação (Sem Docker / Virtualenv)

```bash
# 1. Subir apenas os bancos de dados (desenvolvimento e teste)
docker-compose up db-dev db-test -d

# 2. Criar e ativar o ambiente virtual
python -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate

# 3. Instalar dependências
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Rodar as migrações no banco local
env DATABASE_URL=postgresql+asyncpg://mundoinvest:mundoinvest@localhost:5432/mundoinvest alembic upgrade head

# 5. Iniciar o servidor de desenvolvimento
env DATABASE_URL=postgresql+asyncpg://mundoinvest:mundoinvest@localhost:5432/mundoinvest uvicorn app.main:app --reload --port 8000
```

A API estará disponível em `http://localhost:8000`.  
Documentação interativa (Swagger): `http://localhost:8000/docs`.

### Executar os testes

```bash
# Subir o banco de testes antes de rodar localmente
docker-compose up db-test -d

# Instalar dependências de dev e rodar testes (aponta para PostgreSQL real)
pip install -r requirements-dev.txt
env TEST_DATABASE_URL=postgresql+asyncpg://mundoinvest_test:mundoinvest_test@localhost:5433/mundoinvest_test pytest -v

# Ou inteiramente dentro do container (banco já disponível via Docker Compose)
docker-compose exec api pytest -v
```

---

## 6. Exemplos de Requisição

### POST /clientes

```bash
curl -X POST http://localhost:8000/clientes \
  -H "Content-Type: application/json" \
  -d '{
    "cliente_nome": "João Silva",
    "cliente_email": "joao.silva@example.com",
    "tipo_solicitacao": "Atualização cadastral",
    "valor_patrimonio": 250000
  }'
```

**Resposta esperada (HTTP 201):**
```json
{
  "id": 1,
  "cliente_nome": "João Silva",
  "cliente_email": "joao.silva@example.com",
  "status": "Aguardando Análise",
  "pipefy_mutation_sent": "createCard"
}
```

### POST /webhooks/pipefy/card-updated

```bash
curl -X POST http://localhost:8000/webhooks/pipefy/card-updated \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "evt_123",
    "card_id": "card_456",
    "cliente_email": "joao.silva@example.com",
    "timestamp": "2026-05-18T12:00:00Z"
  }'
```

**Resposta esperada (HTTP 200):**
```json
{
  "event_id": "evt_123",
  "status": "Processado",
  "prioridade": "prioridade_alta",
  "idempotent": false
}
```

**Segunda chamada com mesmo `event_id` (HTTP 200 — idempotente):**
```json
{
  "event_id": "evt_123",
  "status": "Processado",
  "prioridade": "prioridade_alta",
  "idempotent": true
}
```

---
### Notas

¹: [Conceito de Concorrência e Event Loop no FastAPI — Documentação Oficial](https://fastapi.tiangolo.com/async/#concurrent-burgers)   
²: O SQLite, embora excelente para testes e prototipagem, opera em nível de arquivo e possui limitações severas de escrita simultânea (database-level locking), o que inviabiliza seu uso em cenários de alta concorrência de webhooks, onde o PostgreSQL utiliza controle de concorrência multiversão (MVCC) para garantir performance. [Referência: PostgreSQL MVCC Documentation](https://www.postgresql.org/docs/current/mvcc.html)   
³:Este fenômeno é conhecido em arquiteturas Serverless. Referência: [AWS Docs: Avoiding pinning an RDS Proxy
](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy-pinning.html)