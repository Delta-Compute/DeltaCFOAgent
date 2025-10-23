# GitHub Actions Workflows - DISABLED

## Status: DESABILITADOS

Os workflows do GitHub Actions foram **DESABILITADOS** para evitar conflitos com os Cloud Build triggers.

### Motivo da Desabilitação:

- ✅ **Cloud Build triggers** já fazem deploy automático no push
- ⚠️ **GitHub Actions** eram redundantes e causavam conflitos
- 🎯 **Solução**: Manter apenas Cloud Build triggers (funcionando perfeitamente)

### Workflows Desabilitados:

- `deploy-cloud-run.yml.disabled` - Deploy principal
- `deploy-analytics-service.yml.disabled` - Deploy analytics

### Sistema Atual (ATIVO):

```
📤 Push no Git
    ↓
🏗️ Cloud Build Triggers (ÚNICO SISTEMA)
    ├── main branch → deltacfoagent (produção)
    └── Dev branch → deltacfoagent-dev (desenvolvimento)
    ↓
✅ Deploy automático e seguro
```

### Para Reativar (se necessário):

```bash
# Remover .disabled dos nomes dos arquivos
mv deploy-cloud-run.yml.disabled deploy-cloud-run.yml
mv deploy-analytics-service.yml.disabled deploy-analytics-service.yml
```

**Nota**: Só reative se os Cloud Build triggers forem desabilitados primeiro.

---
*Alteração feita em: 2025-10-22*
*Motivo: Resolver conflitos de deploy duplo*