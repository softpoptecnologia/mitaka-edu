# ADR-001 — Avaliação multimodal, offline-first e sincronização segura

**Status:** proposto (Fase 0 — sem implementação)  
**Data:** 2026-08-09  
**Produto:** Mitaka Edu  
**Escopo:** aluno, evidências, instrumentos, sessões, Flutter, API, papel, sync  
**Fora de escopo nesta ADR:** reformular Admin/secretaria/cadastros; OMR; IA; segunda arquitetura de avaliação

---

## 1. Problema

O Mitaka já consegue registrar sondagens digitais e observacionais no Django, pontuar por regras no banco e atualizar a situação longitudinal do aluno (`StudentSkillStatus`). Isso, porém, assume **conexão + player web + PK numérica + uma sessão por vez no servidor**.

A pergunta do produto passou a ser:

> Como obter, registrar e acompanhar evidências confiáveis da aprendizagem de cada aluno, mesmo quando a escola não possui internet, possui poucos dispositivos ou precisa realizar atividades em papel?

Hoje isso quebra em vários pontos:

1. O Flutter é demonstrativo (dados locais hardcoded, sem HTTP, sem SQLite).
2. Não há UUID distribuído; a API de avaliação usa `session_id` inteiro.
3. Não há canal de coleta (online / offline / papel / lançamento manual).
4. `application_mode` já existe, mas significa **adaptação pedagógica**, não origem da evidência.
5. Não há pacote offline, sync idempotente, token de papel nem entrada em lote de avaliação.
6. `StudentSkillStatus` é só o estado mais recente; tendência histórica não está exposta como serviço.
7. Impressão atual é versão acessível do player, sem QR opaco nem lançamento posterior.

O ativo principal são os **dados longitudinais do aluno**. Qualquer evolução deve ampliar o domínio existente, não substituí-lo.

---

## 2. Arquitetura atual

### 2.1 Princípio que já está certo

```
Student (identidade permanente)
  └── Enrollment (contexto anual: escola/turma/ano)
        ├── AssessmentSession → AssessmentResponse → SessionSkillResult
        ├── Evidence
        └── StudentIntervention
StudentSkillStatus (snapshot atual: student × skill)
```

Troca de escola, turma ou ano não apaga a criança. Sessões ficam na matrícula em que ocorreram. Testes críticos já cobrem longitudinalidade e freeze de `matrix_version` na sessão.

### 2.2 Models centrais (raio-X)

#### Student

- **Função:** identidade pedagógica permanente (`external_code` municipal único).
- **Relações:** `enrollments`, `evidences`, `interventions`, `accessibility_profile`, `skill_statuses`, `family_links`.
- **Reutilizar?** Sim, sem mudança estrutural.
- **Ampliar?** Opcional: `external_uuid` só se o app criar aluno offline (não é o caso no MVP; alunos vêm do servidor).

#### Enrollment

- **Função:** vínculo anual aluno–turma–ano. `unique_together (student, school_year)`.
- **Relações:** sessões, evidências, intervenções, `StudentSkillStatus`.
- **Reutilizar?** Sim. Toda evidência avaliativa continua ancorada aqui.
- **Ampliar?** Não nesta fase.

#### AssessmentInstrument

- **Função:** um instrumento pedagógico ligado a **1 skill + 1 matrix_version**.
- **Tipo:** `digital` | `observational` (`instrument_type`).
- **Reutilizar?** Sim — é o único “tipo de avaliação”. Não criar `DigitalAssessment` / `PaperAssessment`.
- **Ampliar?** Sim: `content_version` (inteiro) para freeze de conteúdo offline, distinto da matriz.

#### AssessmentItem / AssessmentOption / ItemAccessRequirement

- **Função:** itens, alternativas, requisitos funcionais de acesso.
- **Reutilizar?** Sim.
- **Ampliar?** UUID opcional nos itens **não** é necessário no MVP (itens não são criados offline; vêm no pacote com PK do servidor).

#### AssessmentItemVariant + VariantAccessRequirement

- **Função:** acomodação ou modificação pedagógica versionada, com equivalência e workflow de aprovação.
- **Reutilizar?** Sim. Pacote offline deve incluir variantes **já resolvidas** ou regras suficientes.
- **Ampliar?** Não nesta fase.

#### AssessmentSession

- **Função:** evento de aplicação. Freeze de `matrix_version`. Snapshot de features (`active_features`, `adaptation_summary`).
- **Status:** `in_progress`, `completed`, `partially_completed`, `not_applicable`, `requires_alternative_instrument`, `accessibility_blocked`, `abandoned`.
- **`application_mode` atual:** `standard` | `adapted` | `observational` — montagem da sessão (acesso), **não** canal de coleta.
- **Reutilizar?** Sim, é o hub de todas as coletas.
- **Ampliar?** Sim: canal de coleta, UUID, `occurred_at`, metadados leves de origem. **Não** reutilizar `application_mode`.

#### AssessmentResponse

- **Função:** raw data do item + trilha de acessibilidade (`variant_used`, `equivalence_applied`, `counts_toward_score`).
- **Constraint:** `unique_together (session, item)`.
- **Reutilizar?** Sim. Barreira ≠ erro já está modelado.
- **Ampliar?** `external_uuid`.

#### SessionSkillResult

- **Função:** resultado pedagógico da sessão (raw_score, max_score, status_code/label, template, nota de a11y).
- **Reutilizar?** Sim — é o histórico interpretado por evento.
- **Ampliar?** Não. Tendência se calcula a partir desta tabela.

#### StudentSkillStatus

- **Função:** snapshot **mais recente** student × skill (`unique_together`).
- **Reutilizar?** Sim, como visão atual — nunca como histórico completo.
- **Ampliar?** Não criar tabela de histórico duplicada. Ajustar **regra de update** (não o schema) para não sobrescrever status mais novo com sessão offline mais antiga.

#### ScoringRule / SkillResultMapping

- **Função:** faixas no banco; mapping para atenção + template.
- **Reutilizar?** Sim. Incluir no pacote offline (versão determinística). Scoring autoritativo permanece no Django.

#### Evidence

- **Função:** foto/áudio/vídeo/texto ligado a aluno + matrícula + skill opcional.
- **Não** está ligado a `AssessmentSession`.
- **Reutilizar?** Sim.
- **Ampliar?** `external_uuid`; FK opcional `session`.

#### InterventionTemplate / StudentIntervention / ClassroomIntervention

- **Função:** intervenção sugerida/aplicada; follow-up em lote já existe (`record_batch_followup`) e **não pontua formalmente**.
- **Reutilizar?** Sim. Lançamento rápido de **avaliação** é outro fluxo (cria sessão + scoring). Não misturar follow-up com assessment.
- **Ampliar?** UUID se intervenção for criada offline (fase posterior). Follow-up offline pode atualizar PK já baixada.

#### StudentAccessibilityProfile / Feature / SupportPlan

- **Função:** necessidades funcionais, sem CID.
- **Reutilizar?** Sim. Pacote offline inclui perfil + features do recorte da turma.
- **Ampliar?** Não.

#### MatrixVersion / Skill / StatusLabelConfig / SkillProgression

- **Função:** matriz versionada; labels configuráveis; progressão conceitual entre skills.
- **Freeze atual:** `AssessmentSession.matrix_version` gravado no `start_session`.
- **Lacuna:** itens do instrumento podem mudar sem nova `MatrixVersion`.
- **Reutilizar?** Sim + `content_version` no instrumento.

#### AuditLog

- **Função:** auditoria genérica (create/update/delete/import/permission/enrollment/instrument/login/accessibility/support_plan).
- **Ampliar?** Novos `Action` (sync, paper, offline) de forma aditiva.

#### TeacherClassroom + selectors

- **Função:** escopo do professor. `apps/accounts/selectors.py` é a regra de ouro.
- **Reutilizar obrigatoriamente** na geração do pacote offline e na API de sync.

### 2.3 Serviços atuais relevantes

| Serviço | Papel |
|---|---|
| `AccessibilityAssessmentResolver` | Decide item padrão vs variante vs bloqueio. Só no Django. |
| `start_session` / `save_response` / `complete_session` | Ciclo de vida. Resume sessão `in_progress` do mesmo enrollment+instrumento. |
| `score_session` | Soma só `counts_toward_score`; atualiza `SessionSkillResult` + `StudentSkillStatus`; recalcula indicadores. |
| `record_batch_followup` | Lote de acompanhamento de intervenção (evidência, sem scoring). |
| `build_student_synthesis` | Necessidade principal + última intervenção + próxima ação. Sem tendência temporal. |
| `classrooms_for_user` / `user_can_access_*` | RBAC de dados. |

### 2.4 APIs atuais

- DRF instalado; autenticação **somente SessionAuthentication**.
- Avaliação: `POST /api/sessoes/<int:id>/responder/` (autosave).
- Professor: `/api/professor/hoje/`, turmas, grupos, aula, follow-up em lote, reavaliações.
- Flutter **não consome** nenhuma API.

### 2.5 Flutter atual (`teacher_app/`)

- Dependências: `provider`, `flutter_tts`. Sem `http`, sem SQLite, sem sync.
- Login/turmas/atividades em `demo_data.dart` / `activity_catalog.dart`.
- Scoring e rótulos pedagógicos **hardcoded** no client (`ActivitySession.pedagogicalLabel`).
- ID de sessão = `millisecondsSinceEpoch`.
- UI fala direto com `AppState` (ChangeNotifier), sem Repository.

### 2.6 Papel atual

`PrintAccessibleAssessmentView` imprime o instrumento **já adaptado** para um aluno. Não há token opaco, QR, agrupamento de turma nem tela de lançamento posterior.

---

## 3. Arquitetura proposta

### 3.1 Princípio

```
                ALUNO
                  ↓
              HABILIDADE
                  ↓
              EVIDÊNCIA (evento)
                  ↓
              EVOLUÇÃO
```

Web, Flutter, offline, papel e observação são **meios**. Todos convergem para:

```
AssessmentSession
  → AssessmentResponse (raw)
  → SessionSkillResult (interpretado)
  → StudentSkillStatus (snapshot atual)
```

Não criar históricos paralelos por canal.

### 3.2 Três eixos ortogonais (não colapsar num campo só)

| Eixo | Campo existente / proposto | Significado |
|---|---|---|
| Natureza do instrumento | `AssessmentInstrument.instrument_type` | `digital` \| `observational` |
| Montagem de acesso | `AssessmentSession.application_mode` | `standard` \| `adapted` \| `observational` |
| Canal de coleta | **`collection_channel` (novo)** | como a evidência foi obtida |

`application_mode` **permanece**. Sobrecarregá-lo com ONLINE/PAPER destruiria o significado atual e os filtros do perfil do aluno (`?modo=adapted`).

### 3.3 `collection_channel`

```text
ONLINE_DIGITAL        player com conexão (web ou app)
OFFLINE_DIGITAL       player local-first no dispositivo
PAPER                 instrumento impresso + lançamento posterior
TEACHER_OBSERVATION   professor preenche escala (respondente = professor)
MANUAL_ENTRY          lançamento posterior sem token de papel
                      (modo rápido ou detalhado)
```

Observação digital offline: `TEACHER_OBSERVATION` + `created_offline=True`.  
Atividade digital offline: `OFFLINE_DIGITAL`.  
Papel + QR: `PAPER`.  
Planilha mental / caderno do professor: `MANUAL_ENTRY`.

Sessões históricas recebem `ONLINE_DIGITAL` (foram aplicadas no player web), preservando `application_mode` original.

### 3.4 Event sourcing pedagógico (leve)

Cada aplicação é um **evento**. Duas sessões da Luna no mesmo dia (tablet A 09:00 e tablet B 10:00) **coexistem**. O snapshot `StudentSkillStatus` reflete a de **maior `occurred_at`**, não a que chegou primeiro no sync.

Não criar `StudentSkillHistory`. O histórico se reconstrói de `SessionSkillResult` (+ evidências + intervenções).

### 3.5 Acessibilidade offline

**Decisão:** o servidor **pré-resolve** o instrumento por aluno no pacote offline.

- Resolver permanece **somente no Django**.
- Pacote inclui, por aluno: features ativas, itens efetivos (padrão ou variante), equivalência, `counts_toward_score` previsto, mídias necessárias, regras de scoring daquela `content_version`.
- Flutter **não reimplementa** `CONFLICT_MAP`.
- Sessão já iniciada no dispositivo **não** é re-resolvida se o perfil mudar no servidor.
- Próximo download do pacote atualiza resoluções futuras.

Isso atende “barreira ≠ erro” sem divergência de regras entre client e server.

### 3.6 Versionamento

| Camada | O que congela | Onde |
|---|---|---|
| Matriz pedagógica | `matrix_version` | já em `AssessmentSession` |
| Conteúdo do instrumento | `content_version` (novo inteiro) | instrumento + snapshot na sessão |
| Pacote offline | `offline_package_version` + `generated_at` | manifest do pacote + log de download |
| Variante usada | `variant_version` | já em `AssessmentResponse` |

Incrementar `content_version` quando itens, opções, requisitos, variantes publicadas ou `ScoringRule` do instrumento mudarem. Sessão offline permanece na versão baixada.

### 3.7 Quatro níveis de funcionamento

| Nível | Contexto | Canal |
|---|---|---|
| 1 | Internet + dispositivos | `ONLINE_DIGITAL` / `TEACHER_OBSERVATION` |
| 2 | Sem internet + dispositivos | `OFFLINE_DIGITAL` / `TEACHER_OBSERVATION` + `created_offline` |
| 3 | Poucos dispositivos | rodízio digital + observação em sequência |
| 4 | Sem dispositivo | `PAPER` → lançamento `MANUAL_ENTRY` ou via token |

Cobertura da turma é **por aluno**, nunca binária “turma feita/não feita”.

---

## 4. Modelos impactados

Ver tabelas 1–5 abaixo. Resumo:

- **Preservar todos** os models listados no pedido (Student … AuditLog).
- **Ampliar** Session, Response, Evidence, Instrument, AuditLog.
- **Não alterar** PKs, não apagar sessões, não remover campos.
- Admin: no máximo exibir canal/UUID/sync; sem reformulação.

---

## 5. Novas entidades necessárias

Só o que o domínio atual **não** cobre sem gambiarra.

### 5.1 `ClassroomInstrumentApplication` (agrupamento operacional)

Não é uma avaliação. É o envelope de uma aplicação de turma (papel, observação em sequência, lançamento em lote).

- classroom, instrument, matrix_version, instrument_content_version
- scheduled_on / applied_on (data pedagógica)
- created_by
- collection_channel predominante
- **sem** status “fechada” obrigatório

Serve para: imprimir turma, ver 7/20 concluídos, continuar outro dia, gerar tokens.

### 5.2 `AssessmentApplicationToken`

Token opaco para papel/QR.

- `token` (ex. `MTK-X82K1P`), único
- enrollment, instrument, application (FK), matrix_version, content_version
- session nullable (preenchida no lançamento)
- **sem** nome, CPF ou dados clínicos no QR

### 5.3 `SyncIngestLog` (observabilidade, não pedagogia)

Registro de tentativas de sync: batch uuid, actor, device, status, counts accepted/duplicate/rejected/conflict, erro resumido. Não substitui `AssessmentSession`.

### 5.4 `TeacherDevice` (fase 2/3)

Identificador do dispositivo vinculado ao professor: `device_id`, last_seen, revoked. Necessário para aparelho compartilhado e wipe no logout. Pode esperar a API offline.

### 5.5 O que **não** criar agora

- `DigitalAssessment` / `PaperAssessment` / `OfflineAssessment` / `ObservationAssessment`
- `StudentSkillStatusHistory` (reconstruir de `SessionSkillResult`)
- `OfflinePackage` persistido como blob obrigatório (gerar on demand; versionar manifest)
- OMR / foto da folha
- Segunda fila de scoring no Flutter como fonte da verdade

---

## 6. Migrations necessárias (proposta — não executar agora)

Princípio: **aditivas, compatíveis, reversíveis**. Campos novos nullable ou com default seguro. Sem drop. Sem mudança de PK.

### Migration A — campos compatíveis + UUID

- `AssessmentInstrument.content_version` (`PositiveIntegerField`, default=1)
- `AssessmentSession.collection_channel` (CharField, default=`online_digital`)
- `AssessmentSession.external_uuid` (UUIDField, unique, **nullable** primeiro)
- `AssessmentSession.occurred_at` (DateTimeField, nullable)
- `AssessmentSession.created_offline` (BooleanField, default=False)
- `AssessmentSession.source_device_id` (CharField, blank, nullable) — identificador opaco do device
- `AssessmentSession.offline_package_version` (CharField, blank)
- `AssessmentSession.instrument_content_version` (PositiveIntegerField, nullable)
- `AssessmentSession.classroom_application` FK nullable
- `AssessmentResponse.external_uuid` (UUIDField, unique, nullable)
- `Evidence.external_uuid` (UUIDField, unique, nullable)
- `Evidence.session` FK nullable

Não colocar `sync_status` na sessão pedagógica: no servidor, existir = já ingerido. Status de fila é preocupação do Flutter.

### Migration B — models auxiliares

- `ClassroomInstrumentApplication`
- `AssessmentApplicationToken`
- `SyncIngestLog` (pode ir na Fase 2 junto com a API)

### Migration C — índices e constraints

Ver tabela 4 e 5.

### Migration D — data migration

- Backfill `external_uuid` em sessões/respostas/evidências existentes (`uuid4`).
- `occurred_at = started_at` (ou `completed_at` se existir).
- `collection_channel = online_digital` para todas as sessões atuais.
- `instrument_content_version = 1` nas sessões existentes.
- `application_mode` **intocado**.
- Instrumentos: `content_version = 1`.

Depois do backfill, tornar `external_uuid` NOT NULL + unique (migration E opcional, só quando o backfill estiver validado).

---

## 7. Estratégia de compatibilidade

1. Player web atual continua usando `start_session` → `ONLINE_DIGITAL` implícito pelo default.
2. Resume de sessão `in_progress` **só** para canal online no mesmo enrollment+instrumento (comportamento atual). Offline/papel **sempre** criam evento novo via UUID.
3. Relatórios, família, indicadores e `score_session` não dependem do novo campo; continuam lendo `SessionSkillResult` / `StudentSkillStatus`.
4. Filtro `?modo=adapted` do perfil do aluno permanece baseado em `application_mode` / `active_features`.
5. Testes críticos atuais (RBAC, freeze, scoring, CSV, longitudinalidade, família) devem continuar verdes sem alteração de fixtures além do default dos novos campos.

---

## 8. Estratégia offline

### 8.1 Escopo do pacote

Professor autentica (quando houver rede) e o app baixa **somente turmas autorizadas** via selectors.

Conteúdo mínimo do pacote da turma:

- escola, ano, turma, professores vinculados
- alunos + matrículas ativas
- skills, labels de status, instrumentos publicados da matriz vigente
- itens, opções, requisitos, variantes utilizáveis
- scoring rules + mappings da `content_version`
- mídias referenciadas (áudios/imagens) com hash
- perfis de acessibilidade + features (rótulos, não CID)
- **instrumento pré-resolvido por aluno**
- intervenções abertas (para follow-up offline, fase posterior)
- `offline_package_version`, `generated_at`, `matrix_version`, lista de `instrument_content_version`

Nunca: toda a rede, outras escolas, laudos, senhas de outros usuários.

### 8.2 Local-first no Flutter

```
UI → Repository → LocalDataSource (SQLite/Drift)
                      ↓
                 SyncService ⇄ RemoteDataSource (Django API)
```

Fluxo de resposta:

```
Aluno responde → SQLite COMMIT → UI confirma → sync assíncrono
```

UI nunca chama HTTP direto. Sem internet, o professor continua. Estados: “Tudo sincronizado” / “N registros aguardando” / “Turma disponível offline”. Sem botão de “modo offline”.

### 8.3 Banco local

Tecnologia recomendada: **Drift** (SQLite type-safe, Isolates, migrações versionadas), compatível com Flutter 3.7+ do projeto. Alternativa: `sqflite` + repositórios manuais (mais frágil).

Fila local (`sync_queue`): uuid, entity_type, entity_uuid, operation, payload, created_at, attempts, last_error, status (`pending|syncing|synced|failed|conflict`).

### 8.4 Scoring no dispositivo

Provisório, só para feedback imediato, usando regras **embutidas no pacote**.  
**Fonte da verdade:** Django `score_session` na ingestão. Client atualiza snapshot local com o resultado oficial.

---

## 9. Estratégia de sincronização

### 9.1 Direção servidor → dispositivo

`GET /api/v1/offline/classrooms/<id>/package/` (nome final alinhado ao prefixo `/api/` existente)

- Auth: token de dispositivo (ver §11 / impacto API).
- Escopo: `user_can_access_classroom`.
- Resposta: manifest + payload (JSON) + URLs de mídia ou pacote compactado.
- Auditar: `offline_package_downloaded`.

### 9.2 Direção dispositivo → servidor

Preferir **um batch**:

`POST /api/v1/sync/batch/`

Payload exemplo:

```json
{
  "batch_uuid": "...",
  "device_id": "...",
  "package_version": "...",
  "sessions": [ { "external_uuid": "...", "enrollment_id": 1, "...": "..." } ],
  "responses": [ { "external_uuid": "...", "session_uuid": "...", "...": "..." } ],
  "evidences": [ { "external_uuid": "...", "...": "..." } ]
}
```

Idempotência:

1. Lookup por `external_uuid`.
2. Existe → confirmar / atualizar só campos permitidos (não duplicar).
3. Não existe → criar.
4. Resposta por item: `accepted` | `duplicate` | `rejected` | `conflict`.

Erro em um item **não** aborta o lote inteiro (salvo falha de auth/schema). `transaction.atomic` **por item** ou savepoints.

Após persistir sessão completada: `score_session` se aplicável (mesmas regras de barreira ≠ erro).

### 9.3 SyncService (Flutter)

Não fazer `if (internet) sendEverything()`. Responsável por: fila, lote, retry com backoff, erro parcial, token expirado, conflito, integridade (não enviar resposta sem sessão), ordem (sessão antes de responses).

### 9.4 Auth offline

Session cookie não serve para app nativo. Introduzir **TokenAuthentication** (DRF) ou JWT com refresh. Offline exige token de longa duração **revogável** + expiração no logout / troca de professor / wipe do banco local. Não armazenar senha em claro.

---

## 10. Estratégia de conflito

| Entidade | Criação offline | Conflito | Resolução |
|---|---|---|---|
| AssessmentSession | UUID novo | dois tablets, mesma criança, horários diferentes | **manter ambas**; snapshot usa maior `occurred_at` |
| AssessmentResponse | UUID + unique (session, item) | mesmo item duas vezes | idempotente; se payload divergir no mesmo UUID → `conflict` (não silently overwrite) |
| Evidence | UUID novo | duplicata de UUID | duplicate; evidências distintas = dois eventos |
| StudentSkillStatus | derivado | sync atrasado de sessão antiga | **não** sobrescrever se `occurred_at` < última sessão aplicada |
| Cadastro admin (aluno, turma) | não criado offline no MVP | — | servidor vence; app só lê |
| Perfil de acessibilidade | não editado offline no MVP | mudança no servidor após download | vale no **próximo** pacote; sessão em andamento congelada |
| Instrumento | não editado no app | v2 publicada no servidor | sessão offline permanece em v1 (`instrument_content_version`) |

Eventos pedagógicos = append-only. Updates administrativos (se vierem no futuro) usariam `updated_at` / versão / ETag. Fora do MVP offline.

`start_session` atual que reutiliza `in_progress` **não** deve ser usado na sync offline (quebraria UUID e multi-dispositivo).

---

## 11. Segurança

- Pacote limitado ao seletor do usuário (professor ≠ rede).
- Sync valida ownership: enrollment da turma do professor; instrumento publicado; item pertence ao instrumento da sessão; opção pertence ao item.
- QR sem PII: só token opaco.
- Banco local: dados de crianças. Drift/SQLite com SQLCipher **avaliar na Fase 3**; no mínimo: wipe no logout, troca de professor, timeout de sessão, não baixar mídia além do necessário.
- Dispositivo compartilhado: `TeacherDevice` + logout limpa fila **já sincronizada**; pendências: avisar antes de apagar.
- AuditLog: `offline_package_downloaded`, `sync_started/completed/failed`, `paper_assessment_created`, `manual_entry_completed`. Sem monitoramento punitivo.
- Não logar payload completo de respostas de alunos em texto claro além do necessário para suporte.

---

## 12. Implicações para Flutter

Fases 3–5. Não improvisar SQLite na Fase 1.

1. Introduzir Repository + Local/Remote datasources.
2. Drift: teacher, school, year, classrooms, students, enrollments, skills, instruments, items, options, variants, a11y, sessions, responses, evidences, sync_queue.
3. Player atual (catálogo demo) passa a consumir instrumentos do pacote Django.
4. Observação em sequência (Luna → Pedro → Maria) sem abrir 25 perfis.
5. Persistência **antes** de qualquer sync.
6. Indicador de fila, não “modo offline”.
7. Remover scoring hardcoded como verdade; usar regras do pacote só como preview.
8. Auth token + refresh; sem depender de cookie Django.

UX web do professor (lançamento rápido, papel, observação) pode chegar **antes** do Flutter (Fase 1), reutilizando os mesmos serviços.

---

## 13. Implicações para API

Estender `/api/` existente; não criar um segundo monólito.

### Fase 1 (web multimodal, ainda sem Flutter)

- Serviços internos: bulk entry, paper token, collection_channel.
- Views HTML: lançamento rápido/detalhado, impressão com token, cobertura da turma.
- API JSON mínima opcional para o player web (já existe autosave).

### Fase 2 (API offline)

| Método | Recurso | Função |
|---|---|---|
| POST | `/api/v1/auth/token/` | emitir token de dispositivo |
| POST | `/api/v1/auth/logout/` | revogar |
| GET | `/api/v1/offline/bootstrap/` | professor + turmas + versões de pacote |
| GET | `/api/v1/offline/classrooms/<id>/package/` | pacote da turma |
| POST | `/api/v1/sync/batch/` | ingestão idempotente |
| GET | `/api/v1/students/<id>/skill-progression/` | tendência (também usável no web) |

Manter APIs atuais de hoje/grupos/follow-up. Follow-up **não** substitui bulk assessment.

Contrato de batch: resposta item a item (`accepted|duplicate|rejected|conflict`) + `batch_uuid` idempotente (`SyncIngestLog`).

---

## 14. Riscos

| Risco | Impacto | Mitigação |
|---|---|---|
| Reusar `application_mode` para canal | Corrompe adaptação × origem; quebra UI `?modo=` | Campo novo `collection_channel` |
| Sync atrasado sobrescreve status mais novo | Histórico longitudinal mentiroso | Comparar `occurred_at` antes de update |
| Duplicar sessão sem UUID | Duas histórias falsas do mesmo tap | UUID + unique + idempotência |
| Reimplementar resolver no Flutter | Barreira vira “erro” divergente | Pré-resolver no pacote |
| Migration destrutiva | Perda do ativo principal | Só aditivo; backfill; testes de regressão |
| Pacote da rede inteira | LGPD + dispositivo compartilhado | selectors + recorte por turma |
| Token de auth eterno | Conta vazada no tablet da escola | revogação, logout wipe, device registry |
| Comparar 3/5 papel com nível 3 observação | Diagnóstico falso | preservar raw + status; tendência considera instrumento/canal; não fundir escalas |
| `start_session` resume `in_progress` vs multi-device | UUID colide ou perde evento | resume só online; offline = insert |
| Flutter demo scoring ≠ Django | Professor vê rótulo que depois muda | preview local explícito; oficial no sync |
| Uma migration gigante | rollback impossível | A/B/C/D |
| Reformar Admin “já que vamos mexer” | atraso e regressão | não mexer além de campos read-only |

---

## 15. Plano de implantação

### Fase 0 — Arquitetura (esta ADR)

Nenhuma migration. Validar com o time: `collection_channel` vs overload de `application_mode`; Drift; token auth; pré-resolução no pacote.

### Fase 1 — Backend multimodal (web)

- Migrations A + D (UUIDs, canal, content_version).
- Serviços: bulk assessment, observação em sequência, paper token + impressão, lançamento rápido/detalhado.
- `score_session` respeita `occurred_at`.
- Perfil do aluno: origem da evidência + síntese (ainda sem Flutter).
- Testes: histórico por canal, idempotência UUID, lote, papel, regressão.

### Fase 2 — API offline

- Migration B/C (application, token, sync log, índices).
- Package endpoint + batch sync + auth token.
- Testes de escopo (professor não baixa/sincroniza turma alheia).

### Fase 3 — Flutter local-first

- Drift, repository, sync queue, persistência real, wipe.

### Fase 4 — Player offline

- Trocar catálogo demo por instrumentos do pacote; a11y do snapshot.

### Fase 5 — Experiência do professor no app

- Status de sync, observação em sequência, lançamento rápido, “turma disponível offline”.

### Fase 6 — Papel

- PDF + QR opaco + lançamento por token; preparar gancho futuro OMR (foto → confirmação), **sem** implementar OMR.

Critério de sucesso: o mesmo aluno evolui em 2026→2027 na mesma habilidade quer a evidência tenha vindo de tablet offline, observação, papel ou web.

---

## TABELA 1 — Models existentes reutilizados

| Model | Função atual | Uso novo | Alteração? |
|---|---|---|---|
| Student | Identidade permanente | Centro do histórico | Não (MVP) |
| Enrollment | Contexto anual | Âncora de toda sessão/evidência | Não |
| AssessmentInstrument | Instrumento único | Mesmo instrumento, vários canais | Sim: `content_version` |
| AssessmentItem / Option | Itens e alternativas | Player online/offline/papel | Não |
| ItemAccessRequirement | Requisitos funcionais | Pré-resolução no pacote | Não |
| AssessmentItemVariant | Acomodação versionada | Snapshot no pacote + response | Não |
| AssessmentSession | Evento de aplicação | Hub multimodal + UUID + canal | Sim (campos aditivos) |
| AssessmentResponse | Raw data + a11y trail | Idempotência offline | Sim: UUID |
| SessionSkillResult | Resultado interpretado do evento | Histórico / tendência | Não |
| StudentSkillStatus | Snapshot atual | Continua snapshot; regra de update | Não (só serviço) |
| ScoringRule / SkillResultMapping | Faixas no banco | Embarcar no pacote; score no Django | Não |
| Evidence | Evidência multimodal | Sync + vínculo opcional à sessão | Sim: UUID + FK sessão |
| InterventionTemplate | Sugestão por skill | Igual | Não |
| StudentIntervention | Intervenção individual | Follow-up offline depois | UUID só se criar offline |
| ClassroomIntervention | Intervenção de turma | Agrupar observação/follow-up | Não |
| StudentAccessibilityProfile / Feature | Acesso funcional | Pacote + pré-resolução | Não |
| MatrixVersion / Skill / StatusLabel | Matriz e nomenclatura | Freeze + labels na tendência | Não |
| TeacherClassroom | Escopo do professor | Recorte do pacote | Não |
| AuditLog | Auditoria | Novos actions | Sim (choices) |
| AggregatedIndicator | Painéis | Recalcular após sync | Não |

## TABELA 2 — Campos novos propostos

| Model | Campo | Tipo | Nullable? | Default | Justificativa |
|---|---|---|---|---|---|
| AssessmentInstrument | content_version | PositiveInteger | não | 1 | Freeze de conteúdo ≠ matriz |
| AssessmentSession | collection_channel | CharField | não | `online_digital` | Origem da evidência; não reusa application_mode |
| AssessmentSession | external_uuid | UUIDField unique | sim→não após backfill | null | Idempotência Flutter |
| AssessmentSession | occurred_at | DateTime | sim | null→started_at | Momento pedagógico ≠ sync |
| AssessmentSession | created_offline | bool | não | False | Metadado de origem |
| AssessmentSession | source_device_id | CharField | sim | blank | Auditoria multi-device; sem PII |
| AssessmentSession | offline_package_version | CharField | sim | blank | Qual pacote gerou a sessão |
| AssessmentSession | instrument_content_version | PositiveInteger | sim | null | Versão efetivamente usada |
| AssessmentSession | classroom_application | FK | sim | null | Agrupar cobertura/papel/lote |
| AssessmentResponse | external_uuid | UUIDField unique | sim→não | null | Idempotência por resposta |
| Evidence | external_uuid | UUIDField unique | sim→não | null | Sync de evidências |
| Evidence | session | FK AssessmentSession | sim | null | Ligar evidência ao evento sem obrigar |
| AuditLog.Action | SYNC / PAPER / OFFLINE | choices | — | — | Observabilidade |

Não adicionar em Session: `sync_status` (é estado da fila local). `synced_at` só faria sentido num log de ingestão.

## TABELA 3 — Novos models propostos

| Model | Por que é necessário | Relacionamentos |
|---|---|---|
| ClassroomInstrumentApplication | Cobertura parcial da turma, impressão e lote sem “fechar” avaliação | classroom, instrument, created_by → sessions, tokens |
| AssessmentApplicationToken | QR/papel opaco sem PII; relançamento sem reconstruir sessão | application, enrollment, instrument → session nullable |
| SyncIngestLog | Idempotência de batch + observabilidade; não polui o domínio pedagógico | actor, device_id, batch_uuid |
| TeacherDevice (Fase 2/3) | Aparelho compartilhado, revogação, wipe | user, device_id, revoked_at |

## TABELA 4 — Índices

| Índice | Justificativa |
|---|---|
| `AssessmentSession.external_uuid` UNIQUE | Lookup idempotente de sync (quente) |
| `AssessmentResponse.external_uuid` UNIQUE | Idem |
| `Evidence.external_uuid` UNIQUE | Idem |
| `(student, skill)` em SessionSkillResult via join session__enrollment — na prática índice `(skill, session)` já unique; para progressão: índice em `SessionSkillResult(skill, status_code)` **não** priorizar agora | Progressão filtra por student através da sessão/enrollment |
| `AssessmentSession(enrollment, instrument, occurred_at)` | Cobertura, “já avaliou?”, timeline |
| `AssessmentSession(collection_channel)` | Só se relatórios por canal forem frequentes; **adiar** até haver query real |
| `AssessmentSession(classroom_application)` | Lista de cobertura da aplicação |
| `AssessmentApplicationToken(token)` UNIQUE | Scan de QR |
| `SyncIngestLog(batch_uuid)` UNIQUE | Retry do mesmo lote |
| `StudentSkillStatus(student, skill)` | Já existe unique_together |

Não indexar `synced_at` na sessão (campo nem deve existir lá). Não indexar `source_device_id` até haver busca operacional.

## TABELA 5 — Constraints

| Constraint | Tipo | Onde |
|---|---|---|
| PK numérica atual | PK | todos os models existentes (preservar) |
| `external_uuid` unique | UNIQUE | Session, Response, Evidence |
| `(session, item)` | UNIQUE (já existe) | AssessmentResponse |
| `(student, skill)` | UNIQUE (já existe) | StudentSkillStatus |
| `(student, school_year)` | UNIQUE (já existe) | Enrollment |
| token unique | UNIQUE | AssessmentApplicationToken |
| batch_uuid unique | UNIQUE | SyncIngestLog |
| FK session → enrollment PROTECT | FK (já existe) | não cascatear apagamento pedagógico |
| FK token.session SET_NULL | FK | lançamento posterior |
| Check `collection_channel` ∈ enum | Check ou choices Django | Session |
| Check token format | validação de serviço, não DB | `^[A-Z0-9-]{6,32}$` |
| Não FK circular instrument ↔ session | — | content_version é inteiro snapshot, não FK extra |

---

## Diagrama ER atual

```
Student 1──* Enrollment *──1 Classroom *──1 School
                │
                ├──* AssessmentSession *──1 AssessmentInstrument *──1 Skill
                │         │                      │
                │         │                      ├──* AssessmentItem ──* AssessmentOption
                │         │                      │         └──* Variant
                │         │                      └──* ScoringRule
                │         ├──* AssessmentResponse (session, item unique)
                │         └──1 SessionSkillResult (session, skill unique)
                ├──* Evidence
                └──* StudentIntervention

Student 1──* StudentSkillStatus *──1 Skill   (snapshot atual)
Student 1──1 StudentAccessibilityProfile ──* Feature
AssessmentSession.application_mode = standard | adapted | observational
AssessmentSession.matrix_version = freeze da matriz
(sem UUID, sem collection_channel, sem token de papel, sem sync)
```

## Diagrama ER proposto

```
Student 1──* Enrollment *──1 Classroom
                │
                ├──* AssessmentSession
                │         │  + collection_channel
                │         │  + external_uuid
                │         │  + occurred_at
                │         │  + created_offline
                │         │  + source_device_id
                │         │  + instrument_content_version
                │         │  + offline_package_version
                │         │  application_mode  (PRESERVADO: standard|adapted|observational)
                │         │
                │         ├──* AssessmentResponse (+ external_uuid)
                │         └──1 SessionSkillResult
                │
                ├──* Evidence (+ external_uuid, session?)
                └──* StudentIntervention

ClassroomInstrumentApplication (envelope operacional, não avaliação)
    ├── classroom, instrument, content_version, channel, date
    ├──* AssessmentSession
    └──* AssessmentApplicationToken (QR opaco → enrollment → session?)

SyncIngestLog / TeacherDevice     ← infra de sync, fora do núcleo pedagógico

StudentSkillStatus                ← snapshot; update só se occurred_at >= último
student_skill_progression()       ← serviço, sem tabela nova
```

Onde fica cada conceito:

| Conceito | Onde |
|---|---|
| application_mode (acesso) | `AssessmentSession` (já existe) |
| collection_channel (origem) | `AssessmentSession` (novo) |
| external_uuid | Session, Response, Evidence (e token) |
| sync metadata (tentativas, erro, status da fila) | Flutter `sync_queue` + `SyncIngestLog` |
| paper application | `ClassroomInstrumentApplication` + `AssessmentApplicationToken` |
| freeze matriz | `AssessmentSession.matrix_version` (já existe) |
| freeze conteúdo | `AssessmentSession.instrument_content_version` |

---

## Decisões explícitas desta ADR

1. **Não** reutilizar `application_mode` para canal de coleta.
2. **Não** substituir PK numérica por UUID; UUID é chave de sync.
3. **Não** criar segunda arquitetura de avaliação.
4. **Não** duplicar histórico em `StudentSkillStatusHistory`.
5. **Não** implementar OMR agora.
6. **Não** reformar o Admin.
7. **Não** baixar a rede inteira no tablet.
8. Resolver de acessibilidade **não** é portado ao Flutter; o pacote leva a atividade já adaptada.
9. Scoring autoritativo permanece no Django; Flutter só preview.
10. Duas sessões no mesmo aluno são dois eventos; conflito administrativo não se aplica a evidências novas.
11. Migrations desta evolução só começam após validação explícita desta ADR (Fase 0).

---

## Testes obrigatórios (a escrever nas fases 1–2)

- Sessão online atualiza habilidade; histórico anterior permanece.
- Sessão offline sincronizada atualiza habilidade.
- Sessão em papel (token) atualiza habilidade.
- Observação atualiza conforme `ScoringRule`.
- UUID de sessão/resposta enviado duas vezes → um registro.
- Sessão offline com `content_version` antiga permanece vinculada.
- Professor não baixa / não sincroniza turma de outro professor.
- Lote de 25 alunos: sucesso; erro de um é reportado sem destruir os demais.
- Barreira de acesso → `counts_toward_score=False`, nunca “errou”.
- `occurred_at` antigo não sobrescreve status mais novo.
- Regressão: `apps.core.tests`, accessibility, reports, teacher journey.

---

## Referências no código atual

- `apps/assessments/models.py` — domínio avaliativo e `application_mode`
- `apps/assessments/services/session.py` — start/save/complete + resume in_progress
- `apps/assessments/services/scoring.py` — score + update `StudentSkillStatus`
- `apps/assessments/services/resolver.py` — acessibilidade
- `apps/analytics/models.py` — snapshot student × skill
- `apps/accounts/selectors.py` — escopo RBAC
- `apps/interventions/api.py` — API professor (session auth)
- `apps/interventions/services/quick_followup.py` — lote **não** avaliativo
- `teacher_app/` — demo local-first incompleto
- `apps/core/tests/test_critical.py` — freeze e longitudinalidade
