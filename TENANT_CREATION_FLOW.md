# Tenant Creation Flow - User Guide

## Como Funciona o "Create New Tenant"

O sistema agora permite que CFOs criem novos tenants (empresas) através de duas formas:

### Método 1: Botão no Menu do Usuário ✨

1. **Localize o Menu**: No canto superior direito de qualquer página, clique no seu nome de usuário
2. **Encontre o Botão**: No menu dropdown, procure por "+ Create New Tenant" (em azul)
3. **Clique**: O botão abrirá automaticamente o Bot de Onboarding

### Método 2: Bot de Onboarding Direto 💬

1. **Ícone do Bot**: Na homepage (`/`), você verá um ícone de chat (💬) no canto inferior direito
2. **Clique no Ícone**: Abre o assistente de onboarding

---

## Fluxo do Bot de Onboarding

O bot guia você através de 3 perguntas simples:

### Passo 1: Nome da Empresa (Obrigatório)
```
Bot: "Welcome! I'm your AI assistant to help set up your business in Delta CFO Agent. Let's get started!"
Bot: "What is your company name?"

Você: [Digite o nome da empresa]
```

### Passo 2: Descrição do Negócio (Opcional)
```
Bot: "Great! Now tell me a bit about your business."
Bot: "What does your company do? (Brief description)"

Você: [Digite uma breve descrição ou pule]
```

### Passo 3: Indústria (Opcional)
```
Bot: "Understanding your industry helps me configure the right financial categories."
Bot: "What industry are you in? (e.g., Technology, Retail, Healthcare, Consulting)"

Você: [Digite a indústria ou pule]
```

### Passo 4: Criação Automática ✅
```
Bot: "Perfect! I'm creating your tenant now..."
Bot: "🎉 Success! Your tenant '[Nome da Empresa]' has been created!"
Bot: "Switching to your new tenant now..."
Bot: "All set! Reloading the page..."

[Página recarrega automaticamente com o novo tenant ativo]
```

---

## Detalhes Técnicos

### API Endpoint
**POST** `/api/tenants`

**Requer Autenticação**: Firebase Bearer Token

**Corpo da Requisição**:
```json
{
  "company_name": "Nome da Empresa",
  "description": "Descrição opcional",
  "industry": "Indústria opcional"
}
```

**Resposta de Sucesso**:
```json
{
  "success": true,
  "tenant": {
    "id": "abc12345",
    "company_name": "Nome da Empresa",
    "description": "Descrição",
    "role": "owner",
    "payment_owner": "cfo",
    "subscription_status": "trial"
  },
  "message": "Tenant created successfully"
}
```

### Restrições de Segurança

1. **Autenticação Obrigatória**: Apenas usuários autenticados podem criar tenants
2. **Tipo de Usuário**: Apenas CFOs (`fractional_cfo`) podem criar novos tenants
3. **CFO como Owner**: O CFO que cria o tenant é automaticamente definido como `owner`
4. **Status Trial**: Novos tenants começam com status `trial`
5. **Pagamento CFO**: Inicialmente, o pagamento fica sob responsabilidade do CFO (`payment_owner: 'cfo'`)

### Permissões Padrão

Quando um CFO cria um tenant:
- **Role**: `owner` (máximo acesso)
- **Pode convidar usuários**: Sim
- **Pode transferir admin**: Sim
- **Pode gerenciar configurações**: Sim
- **Pode gerenciar pagamento**: Sim

---

## Arquivos Modificados

### Frontend
1. **`web_ui/static/onboarding_bot.js`** (NOVO)
   - Bot de onboarding completo
   - Integração com Firebase Auth
   - Gestão de estado e fluxo
   - Chamadas à API de tenants

2. **Templates HTML** (6 arquivos atualizados)
   - `business_overview.html` ✅
   - `cfo_dashboard.html` ✅
   - `dashboard_advanced.html` ✅
   - `files.html` ✅
   - `invoices.html` ✅
   - `revenue.html` ✅
   - `whitelisted_accounts.html` ✅

### Backend
1. **`web_ui/app_db.py`**
   - Registro do blueprint `tenant_bp`
   - Linha 129: Importação
   - Linha 134: Registro

2. **`api/tenant_routes.py`** (Já existia)
   - Endpoint `/api/tenants` (POST)
   - Autenticação e validação
   - Criação de tenant no banco

---

## Onde Está Disponível

O botão "+ Create New Tenant" aparece em **TODAS as páginas** no menu do usuário:

✅ Homepage (`/`)
✅ Transaction Manager (`/dashboard`)
✅ Revenue Recognition (`/revenue`)
✅ Reports (`/reports`)
✅ Invoices (`/invoices`)
✅ Accounts (`/whitelisted-accounts`)
✅ File Manager (`/files`)

---

## Demonstração Visual

### 1. Menu do Usuário
```
┌─────────────────────────────┐
│ John Doe                    │
│ john@example.com            │
├─────────────────────────────┤
│ 🏢 Switch Tenant            │
│   • Delta Capital           │
│   • Company A               │
├─────────────────────────────┤
│ ⚙️  Account Settings         │
│ 👥 Manage Users             │
├─────────────────────────────┤
│ ➕ Create New Tenant        │ <- BOTÃO NOVO!
├─────────────────────────────┤
│ 🚪 Sign Out                 │
└─────────────────────────────┘
```

### 2. Bot de Onboarding
```
┌─────────────────────────────────┐
│ 💬 Business Onboarding          │
│    Tell us about your company   │
├─────────────────────────────────┤
│ Setup Progress: 33%             │
│ [████████░░░░░░░░░░░░░░]        │
├─────────────────────────────────┤
│ 🤖 Bot: Welcome! I'm your AI    │
│        assistant...             │
│                                 │
│ 👤 User: Acme Corporation       │
│                                 │
│ 🤖 Bot: Great! Now tell me...   │
├─────────────────────────────────┤
│ [Type your message...]    [Send]│
└─────────────────────────────────┘
```

---

## Próximas Melhorias Sugeridas

1. **Validação de Nome Único**: Impedir nomes de empresa duplicados
2. **Seleção de Indústria**: Dropdown com indústrias predefinidas
3. **Logo Upload**: Permitir upload de logo durante criação
4. **Email de Boas-Vindas**: Enviar email após criar tenant
5. **Tutorial Interativo**: Guia pós-criação para primeiros passos
6. **Convite Imediato**: Opção de convidar admin durante criação
7. **Configurações Iniciais**: Escolher moeda, timezone, etc.

---

## Troubleshooting

### Bot não abre ao clicar no botão
- **Causa**: Página não tem o bot de onboarding
- **Solução**: Sistema redireciona para homepage (`/?openBot=true`)

### Erro "Authentication required"
- **Causa**: Usuário não está logado
- **Solução**: Fazer login via Firebase

### Erro "fractional_cfo type required"
- **Causa**: Usuário não é CFO
- **Solução**: Apenas CFOs podem criar tenants. Contate um CFO para criar.

### Tenant criado mas não aparece
- **Causa**: Cache ou sessão antiga
- **Solução**: Faça logout e login novamente

---

## Contato e Suporte

Para mais informações ou suporte, consulte:
- **Documentação API**: `/api/tenants` endpoints
- **Código Fonte**: `api/tenant_routes.py`
- **Frontend**: `web_ui/static/onboarding_bot.js`
