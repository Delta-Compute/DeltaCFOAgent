# Firebase Setup Instructions - CFO Users

## Status Atual

✅ **Completo**: Registros no banco de dados PostgreSQL criados
✅ **Completo**: Usuários atribuídos ao tenant Delta com role de CFO
✅ **Completo**: Permissões completas configuradas
⚠️ **Pendente**: Criação de contas Firebase Authentication

## Usuários Criados no Banco de Dados

### 1. Renan Donadon
- **Email**: renan.donadon@leapsolutions.com.br
- **Senha Provisória**: `EvrXvLs3Twk6%14o`
- **Nome**: Renan Donadon
- **Tipo**: Fractional CFO
- **Tenant**: delta
- **Role**: cfo
- **Database ID**: 810450cd-2da5-4357-acb0-857fa12a18c9

### 2. Renan Salomao
- **Email**: renan.salomao@leapsolutions.com.br
- **Senha Provisória**: `&2s1$dVYxTi#LBQS`
- **Nome**: Renan Salomao
- **Tipo**: Fractional CFO
- **Tenant**: delta
- **Role**: cfo
- **Database ID**: 5d812adf-0ff8-4c9b-9074-32641767a7f9

## Passos para Completar o Setup

### Opção 1: Via Firebase Console (Recomendado)

1. **Acesse o Firebase Console**
   ```
   URL: https://console.firebase.google.com
   Projeto: aicfo-473816
   ```

2. **Navegue para Authentication**
   - No menu lateral, clique em "Build" → "Authentication"
   - Clique na aba "Users"
   - Clique no botão "Add User"

3. **Crie o primeiro usuário**
   - Email: `renan.donadon@leapsolutions.com.br`
   - Password: `EvrXvLs3Twk6%14o`
   - Clique em "Add User"
   - **IMPORTANTE**: Copie o UID gerado (ex: `abc123def456...`)

4. **Crie o segundo usuário**
   - Email: `renan.salomao@leapsolutions.com.br`
   - Password: `&2s1$dVYxTi#LBQS`
   - Clique em "Add User"
   - **IMPORTANTE**: Copie o UID gerado

5. **Atualize o banco de dados**

   Execute o script Python:
   ```bash
   python update_firebase_uids.py
   ```

   Ou execute SQL diretamente:
   ```sql
   -- Para Renan Donadon
   UPDATE users
   SET firebase_uid = 'COLE_O_UID_AQUI',
       email_verified = true
   WHERE email = 'renan.donadon@leapsolutions.com.br';

   -- Para Renan Salomao
   UPDATE users
   SET firebase_uid = 'COLE_O_UID_AQUI',
       email_verified = true
   WHERE email = 'renan.salomao@leapsolutions.com.br';
   ```

### Opção 2: Via gcloud CLI (Requer Permissões)

Se você tiver permissões de administrador no Google Cloud:

1. **Adicionar permissões à service account**
   ```bash
   gcloud projects add-iam-policy-binding aicfo-473816 \
     --member="serviceAccount:firebase-adminsdk-fbsvc@aicfo-473816.iam.gserviceaccount.com" \
     --role="roles/firebaseauth.admin"
   ```

2. **Executar script automatizado**
   ```bash
   python complete_firebase_setup.py
   ```

## Verificação Final

Após completar o setup, execute:

```bash
python verify_cfo_users.py
```

Este script verificará:
- ✅ Usuários existem no banco de dados
- ✅ Firebase UIDs foram atualizados
- ✅ Usuários estão atribuídos ao tenant Delta
- ✅ Permissões estão configuradas corretamente

## Permissões Concedidas

Ambos usuários têm acesso completo de CFO:

| Categoria | Permissões |
|-----------|-----------|
| **Transactions** | view, create, edit, delete, export |
| **Invoices** | view, create, edit, delete, approve |
| **Users** | view, invite |
| **Reports** | view, generate, export |
| **Settings** | view, edit |
| **Accounts** | view, manage |

## Enviando Credenciais

**IMPORTANTE**: Envie as credenciais de forma segura:

1. Use um gerenciador de senhas compartilhado (1Password, LastPass, etc.)
2. Ou use email criptografado
3. **NUNCA** envie senhas por email não criptografado
4. Instrua os usuários a mudarem a senha no primeiro login

### Template de Email

```
Assunto: [Delta CFO Agent] Suas credenciais de acesso

Olá [Nome],

Sua conta foi criada no Delta CFO Agent.

Credenciais de acesso:
- Email: [email]
- Senha provisória: [usar método seguro para compartilhar]
- URL de Login: [URL do sistema]

IMPORTANTE:
1. Acesse o sistema usando as credenciais acima
2. Mude sua senha imediatamente no primeiro login
3. Mantenha suas credenciais seguras
4. Se tiver problemas, entre em contato

Seu perfil:
- Tipo de usuário: CFO Fracional
- Tenant: Delta
- Acesso: Completo (CFO)

Atenciosamente,
Equipe Delta CFO Agent
```

## Troubleshooting

### Problema: Usuário não consegue fazer login

**Solução**:
1. Verifique se o Firebase UID foi atualizado no banco de dados
2. Confirme que `email_verified = true`
3. Verifique se `is_active = true`
4. Execute: `python verify_cfo_users.py`

### Problema: Permissões insuficientes

**Solução**:
1. Verifique a tabela `tenant_users`
2. Confirme que `role = 'cfo'`
3. Verifique o campo `permissions` (deve ter 6 categorias)

### Problema: Erro ao criar usuário no Firebase

**Solução**:
1. Use o Firebase Console diretamente
2. Ou adicione permissões à service account:
   - `roles/firebaseauth.admin`
   - `roles/identitytoolkit.admin`

## Scripts Disponíveis

| Script | Descrição |
|--------|-----------|
| `create_cfo_users_db_only.py` | ✅ Cria registros no banco de dados (já executado) |
| `verify_cfo_users.py` | Verifica configuração completa |
| `complete_firebase_setup.py` | Cria contas Firebase (requer permissões) |
| `update_firebase_uids.py` | Helper para atualizar UIDs no banco |
| `CFO_USERS_CREDENTIALS.txt` | Documento com todas as credenciais |

## Próximos Passos

1. ✅ Crie os usuários no Firebase Console (copie os UIDs)
2. ✅ Atualize os UIDs no banco de dados
3. ✅ Execute `python verify_cfo_users.py`
4. ✅ Envie credenciais de forma segura aos usuários
5. ✅ Teste o login de cada usuário
6. ✅ Instrua mudança de senha

## Segurança

- ✅ Senhas fortes geradas automaticamente (16 caracteres)
- ✅ Senhas devem ser mudadas no primeiro login
- ✅ Email verification habilitado
- ✅ Audit log criado para todas as ações
- ✅ Permissões baseadas em roles
- ✅ Isolamento por tenant

## Suporte

Em caso de dúvidas ou problemas:
1. Consulte este documento
2. Execute os scripts de verificação
3. Verifique os logs do sistema
4. Entre em contato com o time de desenvolvimento
