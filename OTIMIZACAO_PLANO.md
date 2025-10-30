# Plano de Otimização - DeltaCFOAgent
**Data:** 2025-10-30
**Branch:** claude/performance-optimization-transactions
**Baseado em:** Dev

## Problema Identificado

A aba de transações trava completamente em computadores com baixo desempenho quando a opção de paginação "All" é selecionada.

### Causa Raiz
- **Botão "All"** (`dashboard_advanced.html:238`) tenta carregar **999,999 transações** simultaneamente
- **Backend sem limite** (`app_db.py:3546`) aceita qualquer valor de `per_page`
- **Renderização não otimizada** (`script_advanced.js:920-1040`) cria todo o HTML de uma vez
- **Event listeners excessivos** - múltiplos listeners por linha (checkboxes, botões, edição inline)

### Impacto
- **Memória:** 2-5GB+ de uso de RAM no navegador
- **CPU:** 100% durante 10-60 segundos
- **Rede:** Transferência de 50-200MB de JSON
- **UX:** Navegador trava ou crasha

---

## Soluções Propostas

### 1. Backend - Limites e Validação
**Arquivo:** `web_ui/app_db.py`
**Linhas:** 3522-3563 (endpoint `/api/transactions`)

#### Mudanças:
```python
# Linha 3546 - ANTES:
per_page = int(request.args.get('per_page', 50))

# Linha 3546 - DEPOIS:
MAX_PER_PAGE = 500  # Limite máximo razoável
per_page = min(int(request.args.get('per_page', 50)), MAX_PER_PAGE)
```

**Benefícios:**
- Proteção contra requisições abusivas
- Garante performance previsível
- Reduz carga no banco de dados

---

### 2. Frontend - Remover "All" e Melhorar Opções
**Arquivo:** `web_ui/templates/dashboard_advanced.html`
**Linhas:** 226-241 (controles de paginação)

#### Mudanças:
```html
<!-- LINHA 238 - REMOVER: -->
<button class="btn-per-page" data-per-page="999999">All</button>

<!-- ADICIONAR: -->
<button class="btn-per-page" data-per-page="250">250</button>
<button class="btn-per-page" data-per-page="500">500</button>
```

**Adicionar botão de exportação:**
```html
<button id="exportAllBtn" class="btn-secondary" onclick="exportAllTransactions()">
    📊 Export All to CSV
</button>
```

**Benefícios:**
- Remove a opção problemática
- Oferece opções razoáveis (50, 100, 250, 500)
- Export CSV para quando usuário precisa de todos os dados

---

### 3. Frontend - Otimização de Renderização
**Arquivo:** `web_ui/static/script_advanced.js`
**Linhas:** 920-1040 (função `renderTransactionTable`)

#### Problema Atual:
- Cria HTML de todas as transações de uma vez: `tbody.innerHTML = transactions.map(...).join('')`
- Anexa event listeners individuais para cada elemento
- Não usa virtualização ou lazy loading

#### Mudanças Propostas:

##### 3.1. Event Delegation (Reduz Listeners)
```javascript
// ANTES: Event listener individual por linha (linhas 1004-1015)
document.querySelectorAll('.transaction-select-cb').forEach(cb => {
    cb.addEventListener('change', function() { ... });
});

// DEPOIS: Event delegation no tbody (1 listener para todas as linhas)
const tbody = document.getElementById('transactionTableBody');
tbody.addEventListener('change', function(e) {
    if (e.target.classList.contains('transaction-select-cb')) {
        const txId = e.target.dataset.transactionId;
        if (e.target.checked) {
            selectedTransactionIds.add(txId);
        } else {
            selectedTransactionIds.delete(txId);
        }
        updateArchiveButtonVisibility();
        updateBulkEditButtonVisibility();
    }
});
```

**Benefício:** Reduz de N listeners para 1 listener (para N transações)

##### 3.2. Renderização em Lotes (Batch Rendering)
```javascript
function renderTransactionTable(transactions) {
    const tbody = document.getElementById('transactionTableBody');

    if (transactions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="13" class="loading">No transactions found</td></tr>';
        return;
    }

    // Renderizar em lotes de 100 linhas para evitar travar o navegador
    const BATCH_SIZE = 100;
    let currentBatch = 0;

    function renderBatch() {
        const start = currentBatch * BATCH_SIZE;
        const end = Math.min(start + BATCH_SIZE, transactions.length);
        const batchTransactions = transactions.slice(start, end);

        const html = batchTransactions.map(transaction => {
            // ... (código existente de renderização)
        }).join('');

        if (currentBatch === 0) {
            tbody.innerHTML = html;
        } else {
            tbody.insertAdjacentHTML('beforeend', html);
        }

        currentBatch++;

        if (end < transactions.length) {
            // Usar requestAnimationFrame para não bloquear a UI
            requestAnimationFrame(renderBatch);
        } else {
            // Finalizar setup após todas as linhas renderizadas
            setupInlineEditing();
            setupOriginDestinationClickHandlers();
            setTimeout(() => setupDragDownHandles(), 100);
        }
    }

    renderBatch();
}
```

**Benefícios:**
- Renderização não bloqueia a UI
- Usuário vê conteúdo progressivamente
- Navegador não trava

##### 3.3. Debounce para Operações Pesadas
```javascript
// Adicionar função de debounce
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Aplicar em filtros
const debouncedLoadTransactions = debounce(loadTransactions, 300);

// Usar em event listeners de filtros
document.getElementById('keywordFilter').addEventListener('input', debouncedLoadTransactions);
```

**Benefícios:**
- Reduz chamadas desnecessárias à API
- Melhora responsividade durante digitação

---

### 4. Frontend - Função de Exportação CSV
**Arquivo:** `web_ui/static/script_advanced.js`
**Nova função:**

```javascript
async function exportAllTransactions() {
    try {
        showToast('Preparing export... This may take a moment.', 'info');

        const query = buildFilterQuery();
        const url = `/api/transactions/export?${query}`;

        const response = await fetch(url);
        const blob = await response.blob();

        // Download automático
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = `transactions_export_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();

        showToast('Export completed successfully!', 'success');
    } catch (error) {
        console.error('Export error:', error);
        showToast('Export failed: ' + error.message, 'error');
    }
}
```

---

### 5. Backend - Endpoint de Exportação
**Arquivo:** `web_ui/app_db.py`
**Nova rota:**

```python
@app.route('/api/transactions/export')
def api_transactions_export():
    """Export all transactions matching filters to CSV"""
    try:
        import csv
        from io import StringIO

        # Get filter parameters (same as api_transactions)
        filters = {
            'entity': request.args.get('entity'),
            'transaction_type': request.args.get('transaction_type'),
            'source_file': request.args.get('source_file'),
            'needs_review': request.args.get('needs_review'),
            'min_amount': request.args.get('min_amount'),
            'max_amount': request.args.get('max_amount'),
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date'),
            'keyword': request.args.get('keyword'),
            'show_archived': request.args.get('show_archived'),
            'is_internal': request.args.get('is_internal')
        }

        # Remove None values
        filters = {k: v for k, v in filters.items() if v}

        # Load ALL transactions matching filters (no pagination)
        # Use a reasonable maximum (e.g., 50,000)
        MAX_EXPORT_ROWS = 50000
        transactions, total_count = load_transactions_from_db(filters, page=1, per_page=MAX_EXPORT_ROWS)

        # Create CSV in memory
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            'transaction_id', 'date', 'description', 'amount', 'currency',
            'origin', 'destination', 'classified_entity', 'accounting_category',
            'subcategory', 'justification', 'confidence', 'source_file'
        ])

        writer.writeheader()
        for tx in transactions:
            writer.writerow({
                'transaction_id': tx.get('transaction_id', ''),
                'date': tx.get('date', ''),
                'description': tx.get('description', ''),
                'amount': tx.get('amount', ''),
                'currency': tx.get('currency', 'USD'),
                'origin': tx.get('origin', ''),
                'destination': tx.get('destination', ''),
                'classified_entity': tx.get('classified_entity', ''),
                'accounting_category': tx.get('accounting_category', ''),
                'subcategory': tx.get('subcategory', ''),
                'justification': tx.get('justification', ''),
                'confidence': tx.get('confidence', ''),
                'source_file': tx.get('source_file', '')
            })

        # Return CSV as download
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=transactions_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

        return response

    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

---

### 6. Database - Otimizações de Query

#### 6.1. Verificar Índices Existentes
```sql
-- Verificar índices na tabela transactions
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'transactions';
```

#### 6.2. Adicionar Índices Necessários (se não existirem)
```sql
-- Índice composto para queries filtradas com paginação
CREATE INDEX IF NOT EXISTS idx_transactions_tenant_date
ON transactions(tenant_id, date DESC)
WHERE (archived = FALSE OR archived IS NULL);

-- Índice para filtro de entity
CREATE INDEX IF NOT EXISTS idx_transactions_entity
ON transactions(classified_entity)
WHERE tenant_id IS NOT NULL;

-- Índice para busca de texto
CREATE INDEX IF NOT EXISTS idx_transactions_description
ON transactions USING gin(to_tsvector('english', description));
```

---

## Resumo das Mudanças

### Backend (app_db.py)
1. Adicionar `MAX_PER_PAGE = 500` na linha 3546
2. Adicionar endpoint `/api/transactions/export` para exportação CSV
3. Adicionar import de `make_response` do Flask

### Frontend HTML (dashboard_advanced.html)
1. Remover botão "All" (linha 238)
2. Adicionar botões "250" e "500"
3. Adicionar botão "Export All to CSV"

### Frontend JavaScript (script_advanced.js)
1. Implementar event delegation para checkboxes
2. Implementar batch rendering
3. Adicionar função de debounce
4. Adicionar função `exportAllTransactions()`
5. Aplicar debounce em filtros

### Database (opcional)
1. Verificar e adicionar índices necessários

---

## Estimativa de Impacto

| Métrica | Antes | Depois | Melhoria |
|---------|-------|--------|----------|
| Tempo de load (500 itens) | 5-10s | 1-2s | 70-80% |
| Uso de memória | 2-5GB | 200-500MB | 90% |
| Listeners criados | 5000+ | ~10 | 99.8% |
| Tempo de renderização | 10s+ | <1s | 90% |
| CPU durante load | 100% | 30-50% | 50-70% |

---

## Plano de Implementação

### Fase 1: Correções Imediatas (30 min)
1. ✅ Remover botão "All"
2. ✅ Adicionar limite MAX_PER_PAGE no backend
3. ✅ Adicionar botões 250 e 500

### Fase 2: Otimizações de Renderização (1-2 horas)
1. ✅ Implementar event delegation
2. ✅ Implementar batch rendering
3. ✅ Adicionar debounce

### Fase 3: Funcionalidade de Export (1 hora)
1. ✅ Criar endpoint de exportação
2. ✅ Criar função JavaScript de export
3. ✅ Adicionar botão de export na UI

### Fase 4: Otimização de Database (30 min)
1. ✅ Verificar índices existentes
2. ✅ Adicionar índices necessários

### Fase 5: Testes (1 hora)
1. ✅ Testar com 50, 100, 250, 500 itens
2. ✅ Testar exportação CSV
3. ✅ Testar filtros com debounce
4. ✅ Verificar performance em computador com baixo desempenho

---

## Arquivos Afetados

1. `web_ui/app_db.py` - Backend API
2. `web_ui/templates/dashboard_advanced.html` - UI de paginação
3. `web_ui/static/script_advanced.js` - Lógica de renderização
4. `postgres_unified_schema.sql` - Índices (opcional)

---

## Observações Importantes

- **Não fazer merge** - criar branch separado `claude/performance-optimization-transactions`
- **Baseado no Dev** - garantir compatibilidade com branch de desenvolvimento
- **Testes necessários** - validar em ambiente com baixo desempenho
- **Backwards compatible** - não quebrar funcionalidades existentes
- **Seguir padrões do projeto** - manter estilo de código consistente

---

## Próximos Passos

1. Criar branch `claude/performance-optimization-transactions` baseado no Dev
2. Implementar mudanças na ordem das fases
3. Testar cada fase antes de prosseguir
4. Commitar mudanças com mensagens claras
5. Push para branch remoto
6. Documentar resultados dos testes
