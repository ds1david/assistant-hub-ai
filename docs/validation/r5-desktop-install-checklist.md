# Validação manual — install / upgrade / uninstall (R5 / issue #66)

**Ambiente**: Windows 10/11 x64, WebView2 presente.  
**Artefatos**: MSI e/ou NSIS de `cargo tauri build` + `SHA256SUMS`.  
**Commit / tag**: _______________  
**Data**: _______________  
**Operador**: _______________

## 0. Pré-check

- [ ] `SHA256SUMS` confere com os arquivos baixados
- [ ] Sidecar real do agent (não stub) se o teste incluir captura de áudio
- [ ] `session-core` acessível se o teste incluir sessão (`http://localhost:8080`)

## 1. Instalação limpa (NSIS por usuário — preferencial)

- [ ] Executar instalador NSIS (`.exe`) **sem** elevação admin (install per-user)
- [ ] Atalho / menu Iniciar cria entrada “Assistant Hub AI — Shell”
- [ ] App abre janela sem console de terminal
- [ ] `%APPDATA%\ai.assistanthub.desktopshell\` recebe config na 1ª execução
- [ ] Nenhum processo órfão óbvio após fechar o app (Task Manager)

## 2. Instalação MSI (opcional)

- [ ] Instalar `.msi` (pode pedir elevação dependendo do escopo)
- [ ] App inicia; desinstalar via “Adicionar ou remover programas”

## 3. Upgrade

- [ ] Com versão N instalada, instalar N+1 (mesmo canal NSIS ou MSI)
- [ ] App inicia; preferências de sessão/provedores **preservadas** ou comportamento documentado
- [ ] Não há duas instalações conflitantes no PATH

## 4. Rollback (documentado)

- [ ] Desinstalar N+1
- [ ] Reinstalar artefato N a partir de release anterior + checksum
- [ ] App inicia na versão N

**Nota**: rollback automático pelo instalador não é requisito desta fatia; o procedimento é reinstalar o artefato anterior verificado por `SHA256SUMS`.

## 5. Remoção

- [ ] Desinstalar via UI Windows
- [ ] Processos do shell encerrados
- [ ] Agent **gerenciado** pelo shell não fica órfão (025)
- [ ] Opção/documentação: preservar vs remover `%APPDATA%` / dados de sessão (se aplicável)

## 6. Negativos

- [ ] Instalador corrompido (bit flip) falha no `sha256sum -c` / hash manual
- [ ] Máquina sem WebView2: mensagem ou falha compreensível (não silêncio)

## Resultado

| Cenário | Pass / Fail / N/A | Notas |
|---------|-------------------|--------|
| Install NSIS | | |
| Install MSI | | |
| Upgrade | | |
| Rollback | | |
| Uninstall | | |
| Checksums | | |

**Conclusão**: ☐ pronto para anunciar release · ☐ bloqueios (listar)
