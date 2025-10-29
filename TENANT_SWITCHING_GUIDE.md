# Guia de Troca de Tenants (Tenant Switching)

## Como Funciona a Troca de Tenants

Quando um usuário tem acesso a múltiplos tenants (como `contato@delta-mining.com` que tem acesso a "delta" e "nascimento"), o sistema permite trocar entre eles.

## Backend API (Já Implementado) ✅

### Endpoint: POST /api/auth/switch-tenant/<tenant_id>

**Requisição:**
```javascript
POST /api/auth/switch-tenant/nascimento
Headers:
  Authorization: Bearer <firebase_id_token>
```

**Resposta de Sucesso:**
```json
{
  "success": true,
  "tenant": {
    "id": "nascimento",
    "company_name": "COMERCIAL NASCIMENTO ALIMENTOS LTDA",
    "description": "...",
    "role": "admin",
    "permissions": {}
  },
  "message": "Switched to tenant successfully"
}
```

**Resposta de Erro (sem acesso):**
```json
{
  "success": false,
  "error": "access_denied",
  "message": "You do not have access to this tenant"
}
```

## Frontend - Como Implementar

### 1. Mostrar Lista de Tenants no Login

Quando o usuário faz login, a API retorna todos os tenants que ele tem acesso:

```javascript
// Resposta do /api/auth/login
{
  "success": true,
  "user": {...},
  "tenants": [
    {
      "id": "delta",
      "company_name": "Delta Renewable Energy",
      "role": "employee"
    },
    {
      "id": "nascimento",
      "company_name": "COMERCIAL NASCIMENTO ALIMENTOS LTDA",
      "role": "admin"
    }
  ],
  "current_tenant": {
    "id": "nascimento",
    "company_name": "COMERCIAL NASCIMENTO ALIMENTOS LTDA",
    "role": "admin"
  }
}
```

### 2. Adicionar Dropdown de Tenant no Navbar

**Localização:** No canto superior direito, ao lado do Account Menu

**Design Sugerido:**
```
┌─────────────────────────────────────┐
│ [Icon] COMERCIAL NASCIMENTO ▼       │
└─────────────────────────────────────┘
    │
    └── Delta Renewable Energy (employee)
        COMERCIAL NASCIMENTO ALIMENTOS LTDA (admin) ✓
```

### 3. Código JavaScript para Switch

```javascript
async function switchTenant(tenantId) {
  try {
    // Mostrar loading
    showLoading('Trocando tenant...');

    // Chamar API
    const response = await fetch(`/api/auth/switch-tenant/${tenantId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${firebaseIdToken}`
      }
    });

    const data = await response.json();

    if (data.success) {
      // Atualizar UI
      updateTenantDisplay(data.tenant);

      // Recarregar dados da página
      location.reload();

      // Ou atualizar dinamicamente
      await loadTenantData(tenantId);
    } else {
      showError(data.message);
    }
  } catch (error) {
    showError('Erro ao trocar tenant');
  } finally {
    hideLoading();
  }
}
```

### 4. Persistência do Tenant Atual

O tenant atual é armazenado na **session** do backend:

```python
# Backend armazena na session
session['current_tenant_id'] = tenant_id
```

Isso significa que:
- ✅ Persiste entre recarregamentos de página
- ✅ Persiste enquanto a sessão estiver ativa
- ❌ É perdido quando o usuário faz logout
- ❌ É perdido quando a sessão expira

### 5. Mostrar Tenant Atual em Todas as Páginas

Adicionar indicador visual em todas as páginas:

```html
<div class="tenant-indicator">
  <i class="fas fa-building"></i>
  <span id="current-tenant-name">COMERCIAL NASCIMENTO ALIMENTOS LTDA</span>
  <span class="tenant-role badge badge-admin">admin</span>
</div>
```

## Exemplo de Implementação Completa

### HTML (Navbar)

```html
<!-- Tenant Switcher -->
<div class="tenant-switcher" style="margin-right: 20px;">
  <button id="tenantSwitcherBtn" class="btn btn-light">
    <i class="fas fa-building"></i>
    <span id="currentTenantName">Carregando...</span>
    <i class="fas fa-chevron-down"></i>
  </button>

  <!-- Dropdown -->
  <div id="tenantDropdown" class="dropdown-menu" style="display: none;">
    <!-- Será preenchido dinamicamente -->
  </div>
</div>
```

### CSS

```css
.tenant-switcher {
  position: relative;
  display: inline-block;
}

.tenant-switcher button {
  background: white;
  border: 1px solid #ddd;
  padding: 8px 15px;
  border-radius: 4px;
  cursor: pointer;
}

#tenantDropdown {
  position: absolute;
  top: calc(100% + 5px);
  right: 0;
  background: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  min-width: 300px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  z-index: 1000;
}

.tenant-option {
  padding: 12px 15px;
  cursor: pointer;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tenant-option:hover {
  background: #f5f5f5;
}

.tenant-option.active {
  background: #e3f2fd;
}

.tenant-role-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 12px;
  background: #2196F3;
  color: white;
}
```

### JavaScript

```javascript
// Inicializar tenant switcher
async function initTenantSwitcher() {
  // Obter tenants do usuário
  const response = await fetch('/api/auth/me', {
    headers: {
      'Authorization': `Bearer ${getFirebaseToken()}`
    }
  });

  const data = await response.json();

  if (data.success) {
    renderTenantSwitcher(data.tenants, data.current_tenant);
  }
}

// Renderizar dropdown de tenants
function renderTenantSwitcher(tenants, currentTenant) {
  const dropdown = document.getElementById('tenantDropdown');
  const currentNameSpan = document.getElementById('currentTenantName');

  // Atualizar nome do tenant atual
  currentNameSpan.textContent = currentTenant.company_name;

  // Limpar dropdown
  dropdown.innerHTML = '';

  // Adicionar cada tenant
  tenants.forEach(tenant => {
    const option = document.createElement('div');
    option.className = 'tenant-option';
    if (tenant.id === currentTenant.id) {
      option.classList.add('active');
    }

    option.innerHTML = `
      <div>
        <div class="tenant-name">${tenant.company_name}</div>
        <small class="text-muted">${tenant.id}</small>
      </div>
      <div>
        <span class="tenant-role-badge">${tenant.role}</span>
        ${tenant.id === currentTenant.id ? '<i class="fas fa-check"></i>' : ''}
      </div>
    `;

    option.onclick = () => switchTenant(tenant.id);
    dropdown.appendChild(option);
  });
}

// Toggle dropdown
document.getElementById('tenantSwitcherBtn').addEventListener('click', (e) => {
  e.stopPropagation();
  const dropdown = document.getElementById('tenantDropdown');
  dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
});

// Fechar dropdown ao clicar fora
document.addEventListener('click', () => {
  document.getElementById('tenantDropdown').style.display = 'none';
});

// Trocar tenant
async function switchTenant(tenantId) {
  try {
    const response = await fetch(`/api/auth/switch-tenant/${tenantId}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getFirebaseToken()}`
      }
    });

    const data = await response.json();

    if (data.success) {
      // Recarregar página para aplicar mudanças
      location.reload();
    } else {
      alert('Erro ao trocar tenant: ' + data.message);
    }
  } catch (error) {
    alert('Erro ao trocar tenant');
  }
}

// Inicializar ao carregar página
document.addEventListener('DOMContentLoaded', initTenantSwitcher);
```

## Teste Manual via cURL

Para testar a API diretamente:

```bash
# 1. Fazer login e obter token
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "id_token": "FIREBASE_ID_TOKEN_AQUI"
  }'

# Resposta incluirá tenants disponíveis

# 2. Trocar para tenant "nascimento"
curl -X POST http://localhost:5001/api/auth/switch-tenant/nascimento \
  -H "Authorization: Bearer FIREBASE_ID_TOKEN" \
  -b cookies.txt \
  -c cookies.txt

# 3. Verificar tenant atual
curl http://localhost:5001/api/auth/me \
  -H "Authorization: Bearer FIREBASE_ID_TOKEN" \
  -b cookies.txt
```

## Verificação de Acesso

O backend verifica automaticamente se o usuário tem acesso ao tenant antes de permitir o switch:

```python
# No backend (auth_routes.py)
query = """
    SELECT tc.id, tc.company_name, tu.role
    FROM tenant_users tu
    JOIN tenant_configuration tc ON tu.tenant_id = tc.id
    WHERE tu.user_id = %s AND tu.tenant_id = %s AND tu.is_active = true
"""
```

Se o usuário não tiver acesso, retorna erro 403.

## Filtro Automático de Dados

Uma vez que o tenant é trocado, **todos os dados** são automaticamente filtrados pelo `current_tenant_id`:

- ✅ Transações financeiras
- ✅ Faturas e invoices
- ✅ Contas bancárias
- ✅ Carteiras cripto
- ✅ Relatórios
- ✅ Configurações

Isso é implementado nos queries do backend:

```python
# Exemplo de query filtrado por tenant
query = """
    SELECT * FROM transactions
    WHERE tenant_id = %s
    ORDER BY date DESC
"""
result = db_manager.execute_query(query, (current_tenant_id,))
```

## Próximos Passos

1. ✅ API backend (já implementado)
2. ⏳ UI do tenant switcher (precisa implementar)
3. ⏳ Indicador visual do tenant atual (precisa implementar)
4. ⏳ Filtro automático de dados por tenant (precisa verificar em cada endpoint)
5. ⏳ Teste end-to-end com múltiplos tenants

## Arquivo para Modificar

Para adicionar a UI de tenant switching, modifique:

**Template Base (se existir):**
- `web_ui/templates/base.html` ou
- `web_ui/templates/layout.html`

**Ou cada template individual:**
- `web_ui/templates/business_overview.html`
- `web_ui/templates/dashboard_advanced.html`
- `web_ui/templates/invoices.html`
- etc.

Adicione o tenant switcher no navbar de cada página.
