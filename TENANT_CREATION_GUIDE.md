# Guia de Criação de Novos Tenants (Clientes)

Este guia explica como criar novos clientes no sistema Delta CFO Agent.

## O que é um Tenant?

Um **tenant** representa uma empresa/cliente no sistema. Cada tenant:
- Tem seus próprios dados isolados
- Tem seus próprios usuários
- Tem suas próprias configurações
- Pode ter múltiplos usuários com diferentes permissões

## Arquitetura Multi-Tenant

```
Delta CFO Agent
├── Tenant: delta (Delta Mining)
│   ├── User: regis@delta-mining.com (owner)
│   ├── User: whit@delta-mining.com (admin)
│   └── User: ariel@delta-mining.com (employee)
│
├── Tenant: nascimento (Comercial Nascimento)
│   ├── User: admin@nascimento.com (owner)
│   └── User: contador@nascimento.com (cfo)
│
└── Tenant: [outro-cliente]
    └── ...
```

## Como Criar um Novo Tenant

### Opção 1: Criar Tenant com Novo Usuário Admin

Use este método quando você quer criar um tenant completamente novo com um usuário administrador que ainda não existe no sistema.

```bash
python create_new_tenant.py \
  --tenant-id nascimento \
  --company-name "COMERCIAL NASCIMENTO ALIMENTOS LTDA" \
  --company-tagline "Alimentos de Qualidade" \
  --company-description "Comercial Nascimento Alimentos - Distribuição de alimentos" \
  --admin-email admin@nascimento.com \
  --admin-name "João Nascimento" \
  --admin-password "SenhaSegura123!"
```

**Parâmetros:**
- `--tenant-id`: ID único do tenant (use letras minúsculas, sem espaços)
- `--company-name`: Nome completo da empresa
- `--company-tagline`: Slogan/descrição curta (opcional)
- `--company-description`: Descrição completa (opcional)
- `--admin-email`: Email do administrador
- `--admin-name`: Nome completo do administrador
- `--admin-password`: Senha inicial do administrador

### Opção 2: Criar Tenant com Usuário Existente

Use este método quando você quer vincular um usuário que já existe no sistema como administrador de um novo tenant.

```bash
python create_new_tenant.py \
  --tenant-id nascimento \
  --company-name "COMERCIAL NASCIMENTO ALIMENTOS LTDA" \
  --admin-email regis@delta-mining.com \
  --admin-name "Regis Dutra" \
  --existing-user
```

**Nota:** O flag `--existing-user` indica que o email já existe no sistema.

## Exemplos Práticos

### Exemplo 1: Criar tenant para Comercial Nascimento

```bash
python create_new_tenant.py \
  --tenant-id nascimento \
  --company-name "COMERCIAL NASCIMENTO ALIMENTOS LTDA" \
  --company-tagline "Alimentos de Qualidade desde 1995" \
  --admin-email joao.nascimento@nascimento.com \
  --admin-name "João Nascimento" \
  --admin-password "Nascimento@2025!"
```

### Exemplo 2: Criar tenant para uma loja de roupas

```bash
python create_new_tenant.py \
  --tenant-id loja-fashion \
  --company-name "Fashion Store LTDA" \
  --company-tagline "Moda e Estilo" \
  --admin-email maria@fashionstore.com \
  --admin-name "Maria Silva" \
  --admin-password "Fashion@2025!"
```

### Exemplo 3: Adicionar tenant para usuário existente (CFO Fracionário)

```bash
# Um CFO fracionário (regis@delta-mining.com) quer gerenciar outro cliente
python create_new_tenant.py \
  --tenant-id cliente-xyz \
  --company-name "Cliente XYZ Serviços LTDA" \
  --admin-email regis@delta-mining.com \
  --admin-name "Regis Dutra" \
  --existing-user
```

## Roles (Funções) Disponíveis

Após criar o tenant, você pode convidar outros usuários com diferentes roles:

1. **owner** (Proprietário)
   - Acesso total ao tenant
   - Pode gerenciar todos os usuários
   - Pode deletar o tenant
   - Pode transferir ownership

2. **admin** (Administrador)
   - Acesso total exceto exclusão do tenant
   - Pode gerenciar usuários
   - Pode configurar integrações

3. **cfo** (CFO/Contador)
   - Acesso completo aos dados financeiros
   - Pode aprovar transações
   - Pode gerar relatórios

4. **cfo_assistant** (Assistente de CFO)
   - Acesso aos dados financeiros
   - Não pode aprovar transações
   - Pode gerar relatórios

5. **employee** (Funcionário)
   - Acesso limitado
   - Pode visualizar dados
   - Não pode fazer alterações críticas

## Verificar Tenants Existentes

Para listar todos os tenants do sistema:

```bash
python list_all_tenants.py
```

## Verificar Usuários de um Tenant

Para listar todos os usuários de um tenant específico:

```bash
python list_tenant_users.py --tenant-id nascimento
```

## Próximos Passos Após Criar Tenant

1. **Verificação de Email**
   - O admin deve verificar seu email no Firebase
   - Link de verificação é enviado automaticamente

2. **Login**
   - Admin pode fazer login em: http://localhost:5001
   - Ou na URL de produção

3. **Configuração Inicial**
   - Configurar informações da empresa
   - Adicionar logo
   - Configurar cores do tema

4. **Convidar Usuários**
   - Via interface web: Settings → Users → Invite
   - Via script: `python invite_user.py`

5. **Importar Dados**
   - Importar transações históricas
   - Importar fornecedores
   - Importar produtos/serviços

## Isolamento de Dados

Cada tenant tem seus dados completamente isolados:

✅ **Isolados por tenant:**
- Transações financeiras
- Faturas (invoices)
- Contas bancárias (bank_accounts)
- Carteiras cripto (wallet_addresses)
- Relatórios
- Configurações

✅ **Compartilhados (se necessário):**
- Usuários (um usuário pode ter acesso a múltiplos tenants)
- Padrões aprendidos pela IA (opcional)

## Segurança e Boas Práticas

1. **IDs de Tenant**
   - Use nomes descritivos mas curtos
   - Apenas letras minúsculas e hífens
   - Exemplos: `delta`, `nascimento`, `loja-fashion`

2. **Senhas**
   - Mínimo 8 caracteres
   - Mistura de letras, números e símbolos
   - Não reutilizar senhas

3. **Emails**
   - Use emails corporativos sempre que possível
   - Evite emails pessoais para contas empresariais

4. **Roles**
   - Dê o mínimo de privilégios necessário
   - Revise periodicamente as permissões
   - Remova usuários inativos

## Troubleshooting

### Erro: "Tenant already exists"
- O tenant_id já está em uso
- Use outro ID ou verifique se o tenant já foi criado

### Erro: "User already exists"
- O email já está cadastrado
- Use `--existing-user` para vincular usuário existente
- Ou use outro email

### Erro: "Failed to create Firebase user"
- Email já está em uso no Firebase
- Senha não atende requisitos mínimos
- Problema de conectividade com Firebase

### Login retorna "User not found"
- Execute: `python sync_firebase_users.py --auto-confirm`
- Execute: `python link_users_to_delta_tenant.py`
- Verifique se o usuário tem vínculo com algum tenant

## Scripts Auxiliares

### Criar Tenant
```bash
python create_new_tenant.py --help
```

### Listar Todos os Tenants
```bash
python list_all_tenants.py
```

### Listar Usuários de um Tenant
```bash
python list_tenant_users.py --tenant-id [tenant-id]
```

### Adicionar Usuário Existente a um Tenant
```bash
python add_user_to_tenant.py \
  --tenant-id nascimento \
  --user-email contador@nascimento.com \
  --role cfo
```

### Remover Usuário de um Tenant
```bash
python remove_user_from_tenant.py \
  --tenant-id nascimento \
  --user-email ex-funcionario@nascimento.com
```

## Suporte

Para ajuda ou dúvidas sobre criação de tenants:
- Email: suporte@delta-mining.com
- Documentação: https://docs.deltacfo.com
- Issues: https://github.com/Delta-Compute/DeltaCFOAgent/issues
