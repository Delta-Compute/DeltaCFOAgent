# Documentação dos Fluxos do Bot de Onboarding

## Estado do Bot (botState)

```javascript
botState = {
    isOpen: false,                     // Bot aberto ou fechado
    currentStep: 0,                    // Passo atual no fluxo (0, 1, 2...)
    userData: {},                      // Dados coletados do usuário
    isProcessing: false,               // Processando uma entrada
    mode: null,                        // 'create_tenant' ou 'configure_tenant'
    currentTenant: null,               // Tenant atual do usuário
    awaitingDocumentResponse: false    // Esperando resposta yes/no após upload
}
```

## Fluxo 1: Criar Novo Tenant (Create Tenant)

**Quando:** Usuário NÃO tem tenant

**Passos:**

```
1. Welcome Screen
   Bot: "What is your company name?"
   Input → userData.company_name

2. Description
   Bot: "What does your company do?"
   Input → userData.description

3. Industry
   Bot: "What industry are you in?"
   Input → userData.industry

4. Chart of Accounts
   Bot: "Create industry-specific categories? (yes/no)"
   Input → userData.use_template

5. Complete
   → Chama completeTenantSetup()
   → POST /api/onboarding/create-tenant
   → Cria tenant no banco de dados
   → Atualiza sessão do usuário
```

## Fluxo 2: Configurar Tenant Existente (Configure Tenant)

**Quando:** Usuário JÁ tem tenant

**Menu Principal:**

```
Bot mostra 4 opções (botões ou texto):

[1] Add Business Entities     → Redireciona para /whitelisted-accounts
[2] Add Bank Accounts          → Redireciona para /whitelisted-accounts
[3] Upload Documents           → Inicia Fluxo 3
[4] Exit                       → Fecha o bot
```

**Processamento:**

```javascript
handleConfigureOption(option)
├─ Se "1" ou contém "entit"    → Redireciona
├─ Se "2" ou contém "bank"     → Redireciona
├─ Se "3" ou contém "upload"   → showDocumentUploadInterface()
├─ Se "4" ou contém "exit"     → closeBot()
└─ Outro                       → Erro: "Please type 1, 2, 3, or 4"
```

## Fluxo 3: Upload de Documentos (Document Upload)

**Passo 1: Mostrar Interface de Upload**

```
showDocumentUploadInterface()
├─ Input de arquivo (accept: .pdf,.doc,.docx,.txt)
├─ Select de tipo:
│  - Contract
│  - Business Report
│  - Invoice
│  - Financial Statement
│  - Other
└─ Botão "Upload & Analyze"
```

**Passo 2: Fazer Upload**

```
handleDocumentUpload()
├─ Valida se arquivo foi selecionado
├─ Mostra "Uploading..."
├─ Prepara FormData:
│  - file
│  - document_type
│  - process_immediately: true
├─ POST /api/onboarding/upload-document
│  └─ Headers: Authorization Bearer token
└─ Aguarda resposta
```

**Passo 3: Processar Resposta do Backend**

```
Backend (api/onboarding_routes.py):
├─ Salva arquivo em uploads/[tenant_id]/[uuid].ext
├─ Insere em tenant_documents table
├─ Se process_immediately = true:
│  ├─ Lê arquivo (PDF ou texto)
│  ├─ Chama Claude AI com prompt de análise
│  ├─ Parse da resposta AI
│  └─ Salva insights em tenant_knowledge table
└─ Retorna: { success, document, knowledge_extracted }
```

**Passo 4: Após Upload Bem-Sucedido**

```
Bot: "Success! Document uploaded and analyzed."
Bot: "I've extracted N insight(s) about your business..."
Bot: "Would you like to upload another document? (yes/no)"

[IMPORTANTE]
botState.awaitingDocumentResponse = true  ← Define estado de espera
```

**Passo 5: Processar Resposta Yes/No**

```javascript
handleDocumentUploadResponse(input)

Se "yes" / "y" / "sim" / "s":
├─ botState.awaitingDocumentResponse = false
├─ Bot: "Great! Please upload your next document."
└─ showDocumentUploadInterface()  ← Mostra interface novamente

Se "no" / "n" / "não" / "nao":
├─ botState.awaitingDocumentResponse = false
├─ Bot: "Perfect! What else would you like to configure?"
└─ Mostra menu principal com botões (1, 2, 3, 4)

Se outro:
├─ Bot: "I didn't understand that. Please answer yes or no."
└─ Permanece com awaitingDocumentResponse = true
```

## Fluxo de Processamento de Input

```javascript
processUserInput(input)

1. Verifica se está esperando resposta de documento:
   if (botState.awaitingDocumentResponse) {
       handleDocumentUploadResponse(input)
       return  ← IMPORTANTE: Sai da função aqui
   }

2. Se mode = 'configure_tenant' e step = 'welcome_existing':
   handleConfigureOption(input)
   return

3. Senão, processa como passo normal do fluxo:
   ├─ Salva em userData
   ├─ Incrementa currentStep
   └─ Mostra próxima mensagem
```

## Bug Anterior (CORRIGIDO)

**Problema:**

Quando o usuário respondia "no" após upload de documento:

```
1. handleDocumentUpload() perguntava: "Upload another? (yes/no)"
2. Usuário digitava "no"
3. processUserInput("no") era chamado
4. Como awaitingDocumentResponse não existia, ia para:
   handleConfigureOption("no")
5. handleConfigureOption não reconhecia "no"
6. Retornava: "I didn't understand that. Please type 1, 2, 3, or 4."
```

**Solução:**

1. Adicionou `awaitingDocumentResponse` ao botState
2. Define `awaitingDocumentResponse = true` após fazer pergunta
3. Em `processUserInput()`, verifica PRIMEIRO se está esperando resposta
4. Chama `handleDocumentUploadResponse()` que processa yes/no corretamente
5. Retorna ao menu principal se "no"

## Variáveis de Estado Importantes

```javascript
// Estados do Bot
botState.mode
├─ null              → Bot ainda não iniciado
├─ 'create_tenant'   → Criando novo tenant (usuário sem tenant)
└─ 'configure_tenant'→ Configurando tenant existente

// Estado de processamento
botState.isProcessing
├─ true   → Bot está processando, não aceita novo input
└─ false  → Bot pronto para receber input

// Estado de upload de documento
botState.awaitingDocumentResponse
├─ true   → Esperando resposta yes/no após upload
└─ false  → Não está esperando resposta de upload
```

## Endpoints do Backend

### POST /api/onboarding/create-tenant
```json
{
  "tenant_id": "company_name",
  "company_name": "Company Name",
  "description": "What the company does",
  "industry": "Technology",
  "entities": [
    {
      "name": "Entity Name",
      "description": "Entity description",
      "entity_type": "subsidiary"
    }
  ]
}
```

### POST /api/onboarding/upload-document
```
Content-Type: multipart/form-data
Authorization: Bearer [firebase_token]

Fields:
- file: [File object]
- document_type: "contract" | "report" | "invoice" | "statement" | "other"
- process_immediately: "true" | "false"
```

Response:
```json
{
  "success": true,
  "document": {
    "id": "uuid",
    "document_name": "filename.pdf",
    "document_type": "contract",
    "created_at": "2025-10-31T14:00:00"
  },
  "knowledge_extracted": [
    {
      "id": "uuid",
      "knowledge_type": "vendor_info",
      "title": "Vendor: Acme Corp",
      "content": "Main supplier for...",
      "confidence_score": 0.95
    }
  ]
}
```

### GET /api/onboarding/entities
Retorna lista de business entities do tenant

### POST /api/onboarding/entities
Cria nova business entity

### GET /api/onboarding/knowledge
Retorna conhecimento extraído de documentos

## Tipos de Conhecimento Extraído

```
knowledge_type:
├─ vendor_info           → Informações sobre fornecedores
├─ transaction_pattern   → Padrões de transações recorrentes
├─ business_rule         → Regras de negócio da empresa
├─ entity_relationship   → Relacionamentos entre entidades
└─ general               → Informações gerais
```

## Tabelas do Banco de Dados

### tenant_documents
```sql
id                  UUID PRIMARY KEY
tenant_id           VARCHAR(100)
document_name       VARCHAR(255)
document_type       VARCHAR(50)
file_path           TEXT
file_size           INTEGER
mime_type           VARCHAR(100)
uploaded_by_user_id VARCHAR(100)
processed           BOOLEAN
processed_at        TIMESTAMP
created_at          TIMESTAMP
```

### tenant_knowledge
```sql
id                    UUID PRIMARY KEY
tenant_id             VARCHAR(100)
source_document_id    UUID (FK → tenant_documents)
knowledge_type        VARCHAR(50)
title                 VARCHAR(255)
content               TEXT
structured_data       JSONB
confidence_score      DECIMAL(3,2)
is_active             BOOLEAN
created_at            TIMESTAMP
updated_at            TIMESTAMP
```

## Uso do Conhecimento Extraído

O conhecimento extraído dos documentos é usado para:

1. **Classificação de Transações**: Melhorar a identificação automática de vendors e categorias
2. **Padrões de Negócio**: Reconhecer transações recorrentes e seus propósitos
3. **Validação**: Alertar sobre transações fora do padrão
4. **Sugestões**: Sugerir classificações baseadas em documentos anteriores

## Exemplo de Fluxo Completo

```
1. Usuário abre o bot
   ↓
2. Bot detecta que usuário tem tenant "delta"
   mode = 'configure_tenant'
   ↓
3. Bot mostra menu com botões: [1] [2] [3] [4]
   ↓
4. Usuário clica "Upload Documents" (opção 3)
   ↓
5. Bot mostra interface de upload
   ↓
6. Usuário seleciona "contract.pdf" e clica "Upload & Analyze"
   ↓
7. Backend processa com Claude AI:
   - Extrai: "Fornecedor XYZ, contratos mensais de R$ 5.000"
   - Salva em tenant_knowledge
   ↓
8. Bot: "Success! I've extracted 1 insight(s)..."
   Bot: "Would you like to upload another document? (yes/no)"
   awaitingDocumentResponse = true
   ↓
9. Usuário digita "no"
   ↓
10. handleDocumentUploadResponse("no") é chamado
    awaitingDocumentResponse = false
    ↓
11. Bot: "Perfect! What else would you like to configure?"
    Mostra menu com botões novamente
    ↓
12. Usuário clica "Exit" (opção 4)
    ↓
13. Bot fecha
```
