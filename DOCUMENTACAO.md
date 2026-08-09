# Mitaka Edu — Documentação completa (raio-X do projeto)

Versão do documento: agosto de 2026  
Público: equipe de desenvolvimento, SME, pitch do desafio e onboarding.

Este texto descreve **tudo o que o repositório tem hoje**, **para que serve** e **como usar cada parte**. Não substitui o código; organiza o sistema para quem precisa operar, demonstrar ou evoluir o MVP.

---

## 1. O que é o Mitaka Edu

Plataforma educacional de **acompanhamento contínuo das habilidades precursoras e iniciais da leitura e escrita**, desenvolvida como MVP para o desafio de inovação aberta da **Secretaria Municipal de Educação de Jucati/PE**.

A ideia central: a complexidade pedagógica fica no sistema (matriz, critérios, instrumentos, acessibilidade). O professor encontra turmas, pendências, resultados e intervenções sugeridas. A Secretaria monitora a rede. A família acompanha a criança **sem notas, sem ranking e sem rótulos clínicos**.

### Ciclo pedagógico

```
Sondagem lúdica → Dados → Intervir → Registrar evidências → Acompanhar → Reavaliar
```

O propósito do sistema é **diagnosticar a escrita/leitura por atividades lúdicas** e gerar dados para intervenção. Planejamento de aula existe como apoio opcional (o edital pede planejamento), mas **não é o CTA principal** do professor.

Na prática isso vira:

1. Sondagem lúdica (web ou app Flutter) — a brincadeira gera os dados
2. Scoring automático (regras no banco, não hardcoded)
3. Situação da habilidade no estudante (`StudentSkillStatus`)
4. Sugestão de intervenção (template por habilidade)
5. Registro de evidências e acompanhamento
6. Reavaliação quando a intervenção já aconteceu
7. Painéis (estudante / turma / escola / rede) + portal da família

### Alinhamento ao edital (8 pontos)

| Ponto | Como o sistema cobre |
|---|---|
| 1. Sondagem lúdica | Instrumentos digitais/observacionais + player web + app Flutter |
| 2. Planejamento | Apoio opcional: painel da turma → insights → intervenção; plano de aula não é o caminho principal |
| 3. Evidências | Foto, áudio, vídeo, texto; opção de compartilhar com a família |
| 4. Painéis | Estudante, turma, escola, rede (HTML + PDF) |
| 5. Intervenção e formação | Templates, intervenções, catálogo de formações |
| 6. Menos retrabalho | Matriz, scoring, sugestões e escopo por papel |
| 7. Multi-dispositivo | Web (Bootstrap/HTMX), PWA, Flutter (Android/Web/Windows) |
| 8. Implantação e uso | Telas Implantação, Uso da rede, Formação continuada |

**Princípio pedagógico:** alfabetizar letrando (Currículo de Pernambuco / BNCC). Sondagens são **demonstrativas**, não clínicas nem validadas psicometricamente.

---

## 2. Como rodar o projeto

### 2.1 Requisitos

- Python 3.11+
- pip
- Opcional: Docker + Docker Compose
- App professor: Flutter SDK 3.7+

### 2.2 Instalação local (SQLite)

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements/local.txt
copy .env.example .env   # ou cp .env.example .env
# No .env local: DATABASE_URL=sqlite:///db.sqlite3

python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Acesse: http://127.0.0.1:8000/

### 2.3 Docker

```bash
cp .env.example .env
# DATABASE_URL=postgres://mitaka:mitaka@db:5432/mitaka
docker compose up --build
```

Aplicação via Nginx: http://localhost:8080/

Serviços do `docker-compose.yml`:

- `db` — PostgreSQL 16
- `redis` — Redis 7 (Celery preparado)
- `web` — Django/Gunicorn
- `nginx` — porta 8080, static/media

### 2.4 App Flutter do professor

```bash
cd teacher_app
flutter pub get
flutter run                 # dispositivo/emulador
flutter run -d chrome       # web
flutter run -d windows      # desktop
```

### 2.5 Testes

```bash
python manage.py test apps.core.tests apps.accessibility.tests apps.reports.tests
```

Cobertura crítica: RBAC, longitudinalidade, freeze da matriz, scoring, CSV, resolver de acessibilidade, privacidade de perfil, preservação histórica de variantes, portal da família e páginas do edital.

### 2.6 Variáveis de ambiente

Arquivos: `.env.example` (local) e `.env.production.example` (cPanel).

| Variável | Função |
|---|---|
| `DJANGO_SECRET_KEY` | Chave Django |
| `DJANGO_DEBUG` | Debug |
| `DJANGO_ALLOWED_HOSTS` | Hosts permitidos |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Origins CSRF (https) |
| `DJANGO_SHOW_DEMO_PROFILES` | Mostra atalhos de login demo |
| `DATABASE_URL` | SQLite ou Postgres |
| `REDIS_URL` / `CELERY_BROKER_URL` | Fila (opcional no MVP) |
| `CELERY_RESULT_BACKEND` | Backend de resultado Celery (default = Redis) |
| `CELERY_TASK_ALWAYS_EAGER` | `True` no local (síncrono); `False` em produção |
| `MEDIA_ROOT` / `STATIC_ROOT` | Arquivos |

`DJANGO_CSRF_TRUSTED_ORIGINS`, `CELERY_RESULT_BACKEND` e `CELERY_TASK_ALWAYS_EAGER` são lidos no código; as duas últimas **não** estão no `.env.example` (têm default). Em produção, `CSRF_TRUSTED_ORIGINS` inclui `https://edu.innomove.com.br` (+ www).

**Nunca versione `.env` com segredos reais.**

### 2.7 Publicar no cPanel

Atualizar o GitHub **não** atualiza o site sozinho.

1. Git Version Control → Pull/Deploy
2. No Terminal do cPanel:

```bash
source ~/virtualenv/edu.innomove.com.br/3.11/bin/activate
cd ~/edu.innomove.com.br
git pull
bash scripts/cpanel_deploy.sh
```

O script roda `migrate`, `collectstatic --clear` e recarrega o Passenger. Sem o `collectstatic`, o HTML novo pode ir ao ar com o CSS antigo (hash `app.xxxx.css`) e o Hoje fica sem cards. Depois: `Ctrl + F5` no navegador (PWA pode cachear CSS antigo).

---

## 3. Arquitetura técnica

### 3.1 Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python, Django 5, DRF (API mínima) |
| Banco | SQLite (dev) ou PostgreSQL (Docker/prod) |
| Front gestão | Django Templates + Bootstrap 5 (layout AdminLTE-like) |
| Front professor web | Templates + Bootstrap 5 + HTMX |
| Front família | Templates simples, linguagem cotidiana |
| Avaliação web | Tela cheia lúdica (`/avaliacao/`) |
| App professor | Flutter (`teacher_app/`) — dados demo locais |
| Infra | Docker Compose, Nginx, Gunicorn, Redis, Celery (preparado) |
| PWA | `static/pwa/manifest.json` + service worker básico |
| PDF | ReportLab (`apps/reports/services/pdf.py`) |

### 3.2 Estrutura de pastas

```
mitaka-edu/
├── apps/                 # apps Django (domínio)
├── config/               # settings, urls, wsgi, asgi, celery
├── templates/            # HTML (não ficam dentro de cada app)
├── static/               # CSS, JS, PWA
├── media/                # uploads (evidências, áudios, imagens)
├── teacher_app/          # Flutter (projeto separado)
├── docker/               # nginx + entrypoint
├── scripts/              # cpanel_deploy.sh
├── requirements/         # base, local, production
├── manage.py
├── README.md             # resumo operacional
└── DOCUMENTACAO.md       # este arquivo
```

### 3.3 Apps Django (`INSTALLED_APPS`)

| App | Responsabilidade |
|---|---|
| `core` | Timestamp, soft delete, audit log, permissões, seed, middleware cPanel |
| `accounts` | User custom, Role, UserProfile, login, portais professor/gestão |
| `schools` | Município, escola, ano letivo, turma, vínculo professor-turma |
| `students` | Estudante permanente, matrícula anual, FamilyLink, import CSV |
| `curriculum` | Matriz pedagógica versionada, dimensões, habilidades, labels |
| `assessments` | Instrumentos, itens, variantes acessíveis, sessões, scoring |
| `accessibility` | Categorias/features, perfil funcional, plano de apoio |
| `evidences` | Evidências de aprendizagem |
| `interventions` | Templates e intervenções (estudante e turma) |
| `planning` | Plano pedagógico assistido + atividades |
| `analytics` | StudentSkillStatus + indicadores agregados + painel SME |
| `reports` | Relatórios HTML/PDF (sem models próprios) |
| `adoption` | Implantação, formação continuada, uso da rede, portal família, home pública |
| `ai` | Stub vazio — MVP sem IA externa |

### 3.4 Settings relevantes

- Idioma: `pt-BR` · fuso: `America/Recife`
- User: `accounts.User`
- CSRF failure custom: `apps.core.views.csrf_failure`
- Middleware extra: `CpanelHttpsMiddleware` (Passenger/SSL)
- Static: WhiteNoise (produção) / StaticFiles simples (local)
- Upload de evidência: tipos JPEG/PNG/WEBP/MP3/WAV/OGG/WEBM/MP4, até 8 MB
- Celery: `CELERY_TASK_ALWAYS_EAGER=True` no local (tudo síncrono)

### 3.5 Context processors

- `branding` → `APP_NAME`, tagline, município, framework curricular
- `navigation` → flags do menu lateral por papel (`nav_flags`)

---

## 4. Mapa de URLs (portais)

Definido em `config/urls.py`.

| URL | Quem usa | O que é |
|---|---|---|
| `/` | Público / redireciona logado | Home do desafio ou portal do papel |
| `/login/` `/logout/` | Todos | Autenticação |
| `/admin/` | Superadmin Django | Admin nativo |
| `/familia/` | Papel FAMILIA | Portal da família |
| `/professor/` | Professor, AEE (e gestão pode entrar) | Portal do professor |
| `/gestao/` | Gestão escolar + rede | Cadastros, matriz, relatórios |
| `/gestao/implantacao/` `/formacoes/` `/uso/` | Rede / gestão | Adoção da plataforma |
| `/secretaria/` | Secretaria, técnico, superadmin | Painéis municipais |
| `/avaliacao/` | Professor | Player de sondagem |
| `/api/sessoes/<id>/responder/` | Professor (HTMX/JS) | Autosave JSON da resposta |

### Roteamento após login

`PublicHomeView` e `HomeRedirectView` (`apps/accounts/views.py` + `apps/adoption/views.py`):

| Papel | Destino |
|---|---|
| FAMILIA | `/familia/` |
| PROFESSOR ou AEE | `/professor/` |
| SECRETARIA, TECNICO, SUPERADMIN | `/secretaria/` |
| GESTOR, COORDENADOR | `/gestao/` |

---

## 5. Papéis, permissões e escopo

### 5.1 Roles (`accounts.Role`)

| Código | Nome | Escopo |
|---|---|---|
| `SUPERADMIN` | Superadministrador | Rede inteira + Django admin |
| `SECRETARIA` | Secretaria Municipal | Rede |
| `TECNICO` | Técnico Pedagógico | Rede |
| `GESTOR` | Gestor Escolar | Escola do perfil |
| `COORDENADOR` | Coordenador Pedagógico | Escola do perfil |
| `AEE` | Atendimento Educacional Especializado | Escola do perfil |
| `PROFESSOR` | Professor | Só turmas vinculadas (`TeacherClassroom`) |
| `FAMILIA` | Família / responsável | Só crianças em `FamilyLink` |

O usuário Django (`accounts.User`) tem `UserProfile` com `role` + `school` opcional.

Aliases aceitos (`ROLE_ALIASES`): “gestora”, “diretora”, “coordenadora”, “professora”, etc.

### 5.2 Grupos de permissão (`apps/core/permissions.py`)

- **NETWORK_ROLES:** SUPERADMIN, SECRETARIA, TECNICO
- **SCHOOL_ROLES:** GESTOR, COORDENADOR, AEE
- **SCHOOL_WRITE_ROLES:** GESTOR, COORDENADOR (escrevem cadastro da escola)
- **MANAGEMENT_ROLES:** rede + escola (sem professor/família)
- **HARD_DELETE:** só SUPERADMIN e SECRETARIA
- **AEE_ROLES:** AEE + coordenação/gestão/rede (plano de apoio)

Mixins: `RoleRequiredMixin`, `ManagementRequiredMixin`, `TeacherRequiredMixin`, `AEERequiredMixin`, `NetworkRequiredMixin`, `FamilyRequiredMixin`.

### 5.3 Selectors (escopo de dados)

`apps/accounts/selectors.py` é a regra de ouro: **toda query de escola/turma/estudante passa por aqui**.

- Rede → vê tudo
- Gestor/coordenador/AEE → só a escola do perfil
- Professor → só turmas com `TeacherClassroom`
- Família → só `FamilyLink` ativo

Funções: `schools_for_user`, `classrooms_for_user`, `students_for_user`, `enrollments_for_user`, `user_can_access_*`.

### 5.4 Acessibilidade (privilégio mínimo)

`apps/accessibility/permissions.py`:

- **Ver recursos funcionais:** professor + gestão + rede (se tiver acesso ao estudante)
- **Editar perfil / plano de apoio:** AEE, coordenador, gestor, técnico, secretaria, superadmin — **não o professor por padrão**
- Família **não** vê perfil clínico nem códigos de feature; vê linguagem simples + evidências compartilhadas

O professor vê **rótulos de recursos** (“Texto ampliado”, “Legendas”), não CID/laudo.

### 5.5 Menu lateral (gestão)

`nav_flags(user)` liga/desliga itens: município, escolas, turmas, estudantes, matrículas, import CSV, professores, anos, matriz, dimensões, alinhamento, instrumentos, templates, indicadores, intervenções, secretaria, relatórios, implantação, formações, uso.

---

## 6. Usuários demonstrativos

Senha de todos: **`demo1234`**  
Criados por `python manage.py seed_demo`.

| Usuário | Perfil | Onde cai |
|---|---|---|
| `admin` | Superadmin (staff/superuser) | Secretaria |
| `secretaria` | Secretaria Municipal | Secretaria |
| `tecnico` | Técnico pedagógico | Secretaria |
| `gestor` | Gestora (EMEI Sol Nascente) | Gestão |
| `coordenador` | Coordenadora (Sol Nascente) | Gestão |
| `aee` | AEE (Sol Nascente) | Portal professor (apoio) |
| `professora` | Ana — Infantil V A/B + turmas Horizonte | Portal professor |
| `professor2` | Bruno — Estrela do Saber | Portal professor |
| `familia` | Lúcia — responsável de Luna Ferreira | Portal família |

A tela de login pode mostrar atalhos desses perfis se `DJANGO_SHOW_DEMO_PROFILES=True`.

---

## 7. Dados de domínio (o que o seed cria)

### 7.1 Rede escolar

- Município: **Jucati/PE** (`slug=jucati`)
- Anos: 2025 (inativo) e **2026 (ativo)**
- Escolas:
  - EMEI Sol Nascente (`ESC001`)
  - EMEI Estrela do Saber (`ESC002`)
  - Escola Municipal Horizonte (`ESC003`)
- Turmas 2026: Infantil V A/B (Sol), Infantil V A + 1º Ano A (Estrela), Infantil IV A + Infantil V A (Horizonte)
- Turma histórica 2025: Infantil IV A (Sol) — usada na trajetória da Luna

~30 estudantes fictícios (`JUC2026001`…). Luna tem matrícula 2025 concluída + 2026 ativa (longitudinalidade).

### 7.2 Matriz pedagógica

Nome: **Matriz Alfabetizar Letrando — PE**  
Versão publicada: `2026-v1-PE`  
Referência: Currículo de Pernambuco / BNCC — Língua Portuguesa (Anos Iniciais)

**Labels de status** (configuráveis, não hardcoded):

| Código | Rótulo |
|---|---|
| `not_observed` | Não observado |
| `needs_support` | Necessita maior mediação |
| `developing_with_support` | Desenvolvendo com apoio |
| `developing` | Em desenvolvimento |
| `demonstrated` | Habilidade demonstrada |

**Dimensões / habilidades (códigos PE):**

| Dimensão | Código | Habilidade |
|---|---|---|
| Oralidade | EF15LP19PE | Recontar oralmente textos literários |
| Leitura/escuta compartilhada | EF15LP03PE | Localizar informações explícitas |
| Vocabulário em uso | EF01LP15PE | Agrupar palavras por significado |
| Consciência fonológica | EF01LP09PE | Comparar sons de sílabas |
| Rimas e jogos sonoros | EF12LP07PE | Identificar rimas em tradição oral |
| Segmentação silábica | EF01LP06PE | Segmentar oralmente palavras em sílabas |
| Sistema de escrita alfabética | EF01LP05PE | Reconhecer a escrita alfabética |

Progressão conceitual no seed:

`oralidade → escuta → vocabulário → consciência fonológica → rimas → segmentação → SEA`

Cada habilidade ganha um **template de intervenção** com atividades lúdicas sugeridas.

### 7.3 Instrumentos de sondagem (demo)

O seed cria três instrumentos + regras de pontuação:

| Instrumento | Tipo | Habilidade |
|---|---|---|
| Sondagem lúdica de rimas (tradição oral) | Digital, 5 itens | EF12LP07PE |
| Reconto oral (observacional) | Observacional | EF15LP19PE |
| Segmentação silábica | Digital, 5 itens | EF01LP06PE |

Variantes publicadas (exemplo): item 2 de rimas com LowVision e NoDrag; item 3 com ScreenReader.

Sessões simuladas nas 6 turmas 2026 (história pedagógica diferente por turma) + Luna em 2025. Depois `rebuild_attention_indicators`. Evidências textuais (Luna visível à família), intervenções individuais, plano da Inf. V B (rimas) e intervenção de segmentação na Inf. V A da ESC002.

### 7.4 Acessibilidade no seed

Perfis funcionais (índices 0–4 do seed ≈ Luna, Theo, Alice, Benício, Helena):

| Estudante | Recursos |
|---|---|
| Luna Ferreira | Texto ampliado + alto contraste |
| Theo Martins | Leitor de tela / áudio |
| Alice Rocha | Sem arrastar + alvos amplos |
| Benício Souza | Menos estímulos + passo a passo |
| Helena Dias | Legendas + instrução visual |

Cada um com plano de apoio AEE + estratégias. Não são diagnósticos clínicos.

### 7.5 Família e adoção

- `FamilyLink`: usuário `familia` → Luna Ferreira (parentesco **mãe**)
- Catálogo de 6 formações continuadas (`ensure_formation_catalog`)

---

## 8. Como fazer cada coisa (fluxos)

### 8.1 Página pública e login

1. Abrir `/` deslogado → `templates/public/home.html` (edital, 8 pontos, público-alvo, ciclo).
2. Clicar **Entrar** → `/login/`.
3. Informar usuário/senha (ou atalho demo).
4. Login grava `AuditLog` (`action=login`) e redireciona para o portal do papel.

Logout: `/logout/` → volta ao login.

### 8.2 Portal do professor (`/professor/`)

Jornada principal: **Hoje → sondagem lúdica → dados → intervenção → acompanhamento → reavaliação**. Planejamento de aula (`/professor/turmas/<id>/planejar-aula/`) fica disponível, mas fora do caminho principal.

**Hoje** (`TeacherHomeView`)

- Fila de ações: sondagens pendentes, atividade lúdica sugerida para o grupo, acompanhamento, reavaliação, aviso de acesso.
- CTA principal: **Iniciar sondagem** / **Iniciar atividade** (abre o player lúdico).
- Sondagens pendentes da turma: `/professor/turmas/<id>/sondagens/`.

**Turmas** → detalhe da turma

- CTA principal: **Iniciar sondagem**.
- Grupos sugeridos: **Iniciar atividade** → `/professor/turmas/<id>/grupos/<skill_id>/` (player por criança + registro de acompanhamento depois).
- Filtros: todos / pendentes / acompanhamento / atenção / apoio (`?apoio=1`).
- Intervenções da turma: `/professor/turmas/<id>/planejamento/` (secundário).

**Perfil do estudante** (`/professor/estudantes/<id>/`)

Abas (query `?tab=`):

- **Geral:** trajetória de matrículas, gráfico de habilidades, status.
- **Sondagens:** instrumentos publicados + sessões. Botão **Iniciar sondagem**.
- **Evidências:** lista + nova evidência.
- **Intervenções:** lista + aceitar template sugerido + nova intervenção + mudar status.
- **Apoio:** recursos funcionais + plano de apoio (edição só AEE/coordenação).

**Como aplicar uma sondagem (web)**

1. Hoje / turma / perfil → **Iniciar sondagem**  
   URL: `/avaliacao/preparar/<enrollment_id>/<instrument_id>/`
2. Tela mostra montagem automática: recursos ativos, quantos itens padrão / equivalentes / alternativos / bloqueados.
3. Opcional: **Imprimir** versão acessível (`/avaliacao/imprimir/...`).
4. **Começar a brincadeira** (POST) → `start_session`  
   - Reaproveita sessão `in_progress` se já existir.  
   - Congela `matrix_version` do instrumento.  
   - Snapshot de `active_features` + `adaptation_summary`.  
   - Modo: `standard`, `adapted` ou `observational`.
5. Player `/avaliacao/sessao/<id>/`  
   - Um item por vez.  
   - Aplica CSS de acessibilidade (`a11y-large-text`, etc.).  
   - Itens incompatíveis são **auto-registrados como N/A** (não contam como erro).  
   - Resposta: POST `/avaliacao/sessao/<id>/responder/` (também em `/api/...`).
6. Concluir → `complete_session` + `score_session` → tela de resultado.

**Como registrar evidência**

1. Perfil → Evidências → Nova.
2. Preencher descrição, habilidade opcional, arquivo opcional.
3. Marcar **visível para a família** se quiser compartilhar (`visible_to_family`).
4. Tipo inferido pela extensão (foto/áudio/vídeo) ou texto.

**Como criar intervenção**

- Depois da sondagem: o sistema sugere template da habilidade.
- No grupo: após a brincadeira, **Registrar acompanhamento** (não substitui a sondagem formal).
- **Manual:** formulário com habilidade, objetivo, atividades, datas.
- Status: planejada → em andamento → concluída / cancelada (`/professor/intervencoes/<id>/status/`).

**Como planejar a turma (opcional)**

1. Turma → Intervenções (`/professor/turmas/<id>/planejamento/`).
2. O sistema lista habilidades com % de crianças em atenção + template sugerido.
3. POST cria:
   - `ClassroomIntervention`
   - `PedagogicalPlan`
   - `PlanActivity` (uma por linha do template)
4. Plano de aula (`/professor/turmas/<id>/planejar-aula/`) é apoio, não o problema central.

**Como o AEE edita apoio**

1. Login `aee` (ou coordenador/gestor).
2. Perfil do estudante → aba Apoio.
3. Marcar features + notas pedagógicas (sem CID).
4. Criar plano de apoio + estratégias (`SupportPlan` / `SupportStrategy`).

### 8.3 Portal da gestão (`/gestao/`)

Dashboard: escolas, turmas, estudantes, cobertura avaliativa, crianças em atenção, gráfico por escola.

**Cadastros (CRUD com soft delete)**

Quem escreve rede: SECRETARIA/TECNICO/SUPERADMIN.  
Quem escreve escola: GESTOR/COORDENADOR na própria escola.  
Hard delete: só SUPERADMIN/SECRETARIA.

| Recurso | URLs típicas | Observação |
|---|---|---|
| Municípios | `/gestao/municipios/` | Só rede |
| Escolas | `/gestao/escolas/` | Arquivar / excluir |
| Turmas | `/gestao/turmas/` | Filtro escola + busca |
| Estudantes | `/gestao/estudantes/` | Filtro atenção / inativos |
| Matrículas | `/gestao/matriculas/` | 1 estudante × 1 ano letivo |
| Professores / equipe | `/gestao/professores/` | User + papel + vínculo turma |
| Anos letivos | `/gestao/anos-letivos/...` | Só um `is_active` por vez |

**Cadastro de equipe (`views_teachers.py` + `TeacherForm`)**

- GESTOR/COORDENADOR só cadastram **PROFESSOR** e **AEE** da própria escola.
- Rede cadastra papéis da escola; só **SUPERADMIN** cria outro SUPERADMIN.
- Papéis GESTOR / COORDENADOR / AEE / PROFESSOR **exigem escola**.
- Senha obrigatória na criação; em edição, em branco = manter.
- Arquivar = `is_active=False`. Hard delete só SUPERADMIN/SECRETARIA.
- Vínculo professor/AEE ↔ turma: `/gestao/professores/vincular/` e excluir vínculo.

**Exclusão bloqueada (prefira desativar)**

- Estudante com matrículas → não hard-delete.
- Matrícula com sessões de avaliação → não hard-delete.
- Escola com turmas / turma com matrículas → não hard-delete.

**Importar estudantes (CSV)**

1. `/gestao/matriculas/importar/`
2. Escolher ano letivo + arquivo CSV UTF-8.
3. Cabeçalhos obrigatórios (minúsculos):

```
matricula,nome,escola,turma,ano_letivo
```

Opcional: `data_nascimento` (`YYYY-MM-DD`, `DD/MM/YYYY` ou `DD-MM-YYYY`).

4. `escola` = código da escola (`ESC001`).  
5. `turma` = nome exato da turma no ano.  
6. Upsert do estudante por `matricula` (`external_code`) + matrícula do ano.  
7. Erros por linha ficam em `ImportError` (não aborta o lote inteiro).

**Novo ano letivo (longitudinalidade)**

`/gestao/anos-letivos/novo/`

- Criar/ativar ano (ativar desliga os outros).
- Matricular estudante em turma do novo ano **sem apagar** matrículas antigas. Matrículas ativas de outros anos viram `completed`.

Regra: identidade do estudante é permanente; o contexto anual é a `Enrollment`.

**Currículo**

- Matriz e versões: criar, editar, **publicar versão** (freeze).
- Dimensões e habilidades: CRUD na versão publicada.
- Alinhamento PE: `/gestao/alinhamento-curricular/` (princípios + progressão).
- Instrumentos: criar, editar, itens, arquivar. Ao **publicar**, `ensure_default_scoring` cria faixas 0–40% / 40–80% / 80–100% se ainda não houver regras.
- Templates de intervenção: CRUD (rede **ou** coordenador).

**Indicadores e intervenções (visão gestão)**

- `/gestao/indicadores/` — `AggregatedIndicator` (atenção % e cobertura) por escopo.
- `/gestao/intervencoes/` — lista estudante + turma.

**Relatórios**

`/gestao/relatorios/`

- Estudante `/gestao/relatorios/estudante/<id>/`
- Turma `/gestao/relatorios/turma/<id>/`
- Escola `/gestao/relatorios/escola/<id>/`
- Rede `/gestao/relatorios/rede/`

HTML na tela. PDF: acrescentar `?formato=pdf` (ReportLab, cabeçalho Mitaka Edu).

### 8.4 Portal da Secretaria (`/secretaria/`)

Só NETWORK_ROLES.

| Tela | URL | Função |
|---|---|---|
| Dashboard municipal | `/secretaria/` | Recortes + indicadores + PDF |
| Comparação de escolas | `/secretaria/comparacao/` | Comparar com cuidado ético (não ranking punitivo) |
| Necessidades pedagógicas | `/secretaria/necessidades/` | Habilidades em atenção na rede |
| Navegação (drill-down) | `/secretaria/navegacao/` | Rede → escola → turma → matrículas |
| Alinhamento curricular | `/secretaria/alinhamento-curricular/` | Mesma visão PE/BNCC |

Filtros GET (`parse_secretaria_filters`): `ano`, `escola`, `turma`, `serie`, `habilidade`, `recorte` (`all` / `atencao` / `acesso`). Turma deve pertencer à escola do recorte.  
Snapshot: `build_secretaria_snapshot` (cobertura, atenção, ranking contextual: estudantes se turma; turmas se escola; escolas se rede).  
PDF: `build_secretaria_pdf` com o **mesmo recorte**.

Indicadores de acessibilidade agregados (`network_accessibility_stats`): sessões adaptadas, cobertura de variantes, bloqueios — **sem rotular criança**.

### 8.5 Implantação, formação e uso (`/gestao/...`)

| Tela | Quem | O que mostra |
|---|---|---|
| Implantação | Rede | Snapshot de adoção + roteiro de implantação |
| Formação continuada | Gestão + rede | Catálogo filtrável por público |
| Uso da rede | Rede | Logins 30d, cobertura de turmas, evidências, planos, famílias |

`adoption_snapshot()` calcula (últimos 30 dias quando couber):

- professores ativos (login no audit)
- % de turmas com sessão concluída
- evidências totais e compartilhadas com família
- planos, intervenções, vínculos familiares, formações

Catálogo padrão de formações (criado on-demand):

1. Sondagens lúdicas (professores)
2. Planejamento a partir da matriz PE/BNCC (professores)
3. Acompanhamento pedagógico na escola (coordenação)
4. Gestão escolar com evidências (gestão)
5. Painéis da rede (técnico/SME)
6. Família na rede: acompanhar sem comparar (famílias)

### 8.6 Portal da família (`/familia/`)

Só papel FAMILIA.

1. Home: cards das crianças vinculadas, tom (`attention` / `ok` / `pending`) e frase em linguagem simples.
2. Criança: `/familia/crianca/<id>/`
   - Headline sem nota
   - Evidências com `visible_to_family=True`
   - Dicas para casa geradas pelas habilidades (parlendas, palmas nas sílabas, reconto, “quem/onde/o quê”)
   - Intervenções recentes em linguagem cuidadosa
3. Tentativa de ver outra criança → redireciona para home.
4. Tentativa de abrir `/gestao/` ou `/secretaria/` → 403.

**O que a família NÃO vê:** pontuação bruta, CID, perfil de acessibilidade técnico, ranking, comparação com outras crianças.

### 8.7 Admin Django (`/admin/`)

Útil para superadmin ajustar models pontuais. O fluxo de produto é pelos portais `/gestao/` e `/professor/`.

---

## 9. Avaliação em profundidade

### 9.1 Modelos

- `AssessmentInstrument` — digital ou observacional; ligado a 1 skill + 1 matrix_version; `time_is_construct` (raro; tempo quase nunca pontua)
- `AssessmentItem` — tipos: image_select, audio_image, image_choice, single_select, visual_tf, observation_scale, **select_then_match** (alternativa sem drag)
- `ItemAccessRequirement` — requisitos funcionais (visão, áudio, drag, leitura, cor, tempo) e suportes (screen reader, teclado)
- `AssessmentOption` — alternativas com `score_value` / `is_correct`
- `AssessmentItemVariant` — acomodação ou modificação pedagógica; equivalência EQUIVALENT / ALTERNATIVE / NOT_EQUIVALENT; workflow DRAFT → … → PUBLISHED; versionada
- `AssessmentSession` — freeze da matriz; modos standard/adapted/observational; snapshot de features
- `AssessmentResponse` — trilha imutável: item original, variante, versão, equivalência, `counts_toward_score`, tempo e repetições (metadado)
- `SessionSkillResult` — resultado da sessão + template recomendado + nota de acessibilidade
- `ScoringRule` + `SkillResultMapping` — faixas de score no banco

Status de sessão relevantes:

- `in_progress`, `completed`, `partially_completed`
- `not_applicable`, `requires_alternative_instrument`, `accessibility_blocked`
- `abandoned`

### 9.2 Resolver de acessibilidade

Classe: `AccessibilityAssessmentResolver` (`apps/assessments/services/resolver.py`).

Para cada item + estudante:

1. Lê features ativas do `StudentAccessibilityProfile`.
2. Se o item padrão é acessível → usa STANDARD.
3. Senão, busca variante **EQUIVALENT** aprovada/publicada compatível.
4. Senão, variante **ALTERNATIVE** com justificativa.
5. Senão → **REQUIRES_ALTERNATIVE** / bloqueado: `counts_toward_score=False`. **Nunca marca como errado.**

Mapa de conflito (exemplos): leitor de tela × item só visual; sem-arrastar × drag; sem limite de tempo × item cronometrado; legendas/Libras × item só áudio.

### 9.3 Scoring

`score_session` (`apps/assessments/services/scoring.py`):

1. Soma só respostas com `counts_toward_score=True`.
2. Max score só dos itens efetivamente pontuáveis naquela sessão.
3. Ignora tempo e número de repetições de instrução.
4. Aplica `ScoringRule` do instrumento; se não houver, fallback por razão (≥0.9 demonstrada, ≥0.5 desenvolvendo, senão necessita mediação). Instrumentos recém-publicados recebem faixas padrão 0–40 / 40–80 / 80–100 (`ensure_default_scoring`).
5. Atualiza `StudentSkillStatus` (visão longitudinal da habilidade).
6. Recomenda template se status ≠ `demonstrated` (`recommend_template_for_result` — sem IA).
7. Recalcula indicadores agregados (`refresh_indicators_for_session`).

Se **nenhum** item pontuável: status `not_observed`, **sem inventar baixo desempenho**.

Se a sessão inteira é bloqueio de acessibilidade / N/A: **não chama** `score_session`.

### 9.4 API

Única rota DRF/JSON de produto: responder item da sessão (session auth). Não há API REST completa de cadastros no MVP. O Flutter **ainda não consome** essa API.

---

## 10. Acessibilidade e inclusão (app `accessibility`)

### 10.1 Conceito

Armazena **necessidades funcionais de acesso**, não diagnósticos. Proibido no modelo: CID, laudos, dados clínicos.

### 10.2 Catálogo

Categorias: Visual, Auditiva, Motora, Cognitiva/atenção, Sensorial, Comunicação.

Features (códigos estáveis):

- Visual: leitor de tela, alto contraste, texto ampliado
- Auditiva: legendas, instrução visual, Libras
- Motora: alvos ampliados, teclado, sem arrastar
- Cognitiva: instruções curtas, tempo extra, passo a passo, sem limite de tempo, repetir instrução
- Sensorial: menos movimento, menos estímulos

Cada feature pode ter `css_class` aplicada no player (`static/css/accessibility.css`).

`ensure_default_features()` (catalog) garante o catálogo no seed e na aba Apoio.

### 10.3 Perfil e plano

- `StudentAccessibilityProfile` 1:1 com estudante
- `StudentAccessibilityFeature` (features ativas + prioridade)
- `StudentSupportPlan` por ano letivo (draft/active/review/completed/archived)
- `StudentSupportStrategy` (estratégia pedagógica, opcionalmente ligada a uma feature)

`set_student_features` grava perfil + audit log (`ACCESSIBILITY`).

---

## 11. Indicadores e relatórios

### 11.1 StudentSkillStatus

Última situação conhecida de **estudante × habilidade** (status, label, needs_attention, última sessão, scores). É o que alimenta badges do professor, família (em linguagem simples) e painéis.

### 11.2 AggregatedIndicator

Escopos: `network`, `school`, `classroom`, `student`.  
Métricas principais:

- `attention_pct` — % em atenção
- `assessment_coverage_pct` — % de cobertura avaliativa

Recalculados ao concluir sessão e no fim do `seed_demo` (`rebuild_attention_indicators`).

### 11.3 Relatórios PDF/HTML

`apps/reports` não tem models. Serviços:

- `student_report_data` / `classroom_report_data` / `school_report_data` / `network_report_data`
- `build_*_pdf` com layout único (teal Mitaka, tabelas, rodapé pedagógico)

Quem pode gerar: professor (escopo das turmas), AEE/gestão (escola), rede (tudo).

---

## 12. Evidências, intervenções e planejamento

### Evidência

Campos: enrollment, student, skill opcional, recorded_by, description, file, file_type, `visible_to_family`.

### Intervenção

- `InterventionTemplate` por skill (atividades uma por linha, duração sugerida em dias)
- `StudentIntervention` e `ClassroomIntervention` (status planned/in_progress/completed/cancelled)
- Recomendação: `recommend_template_for_result` — primeiro template ativo da skill se status ≠ demonstrada (regra local, sem IA)

### Planejamento

- `PedagogicalPlan` da turma, opcionalmente ligado à intervenção de turma
- `PlanActivity` checklist

---

## 13. Core: auditoria, cadastro, bootstrap

### Models base

- `TimeStampedModel` — created_at / updated_at
- `SoftDeleteModel` — `is_active` + `archived_at` + método `archive()`
- `AuditLog` — create/update/delete/import/permission/enrollment/instrument/login/accessibility/support_plan

### Serviços

- `apps/core/services/audit.py` — `log_action`
- `apps/core/services/cadastro.py` — helpers de CRUD + audit nas telas de gestão
- `apps/core/services/bootstrap.py` — `ensure_platform_catalog()` = roles + catálogo de acessibilidade (pode rodar **sem** `seed_demo`)
- Migration `0004_bootstrap_roles` + `0005_familia_role`
- `post_save` User → `ensure_user_profile` cria `UserProfile` vazio

### Middleware

`CpanelHttpsMiddleware`: se o Passenger manda `HTTPS=on` sem `X-Forwarded-Proto`, força HTTPS para cookies CSRF/session funcionarem atrás do proxy.

---

## 14. App Flutter (`teacher_app/`) — Mitaka Atividades

Projeto **separado** do Django. Pacote: `mitaka_teacher`.  
Dependências: `provider`, `flutter_tts`, Material 3, localização pt-BR.

**Esta versão é 100% demo local.** Login e turmas estão em `lib/data/demo_data.dart`, alinhados ao seed, mas **não há HTTP** para a API Django. Próximo passo natural: integrar `/api/` e sessões reais.

### Princípios de UX

- Poucos toques, botões grandes, linguagem clara
- **Sem degradês** (contraste / hipersensibilidade visual)
- **Sem arrastar e soltar**
- **Sem cronômetro**
- Acomodação de acesso **não reduz** status pedagógico
- Modo **Praticar** (estrelas) vs **Sondagem** (sem certo/errado na tela da criança)

### Telas

| Tela | Arquivo | Função |
|---|---|---|
| Login | `login_screen.dart` | `professora` / `professor2` + `demo1234` |
| Shell | `shell_screen.dart` | Bottom nav: Início, Turmas, Atividades, Ajustes |
| Início | `home_screen.dart` | Totais pendente/ok/atenção |
| Turmas | `classrooms_screen.dart` | Lista |
| Detalhe turma | `classroom_detail_screen.dart` | Estudantes + recursos |
| Estudante | `student_detail_screen.dart` | Perfil funcional + iniciar atividade |
| Catálogo | `activity_catalog_screen.dart` | 7 jogos |
| Preparar | `activity_prepare_screen.dart` | Mostra adaptações que o app vai aplicar |
| Player | `activity_player_screen.dart` | Item a item + TTS + Libras hint + passo a passo |
| Resultado | `activity_result_screen.dart` | Status pedagógico + observação da professora |
| Ajustes | `settings_screen.dart` | Forçar texto grande, contraste, menos movimento, TTS |

Estado: `AppState` (ChangeNotifier). Sessões e login **não persistem** (só memória). Fechar o app zera histórico.

Demo local: 6 turmas × 5 alunos = 30 estudantes (mesmos nomes do seed). `professora` vê Sol Nascente + Horizonte; `professor2` vê Estrela do Saber.

### Layouts de item (`PromptLayout`)

| Layout | Interação | Jogos |
|---|---|---|
| `audioImage` | 2 opções + TTS | Rimas, Quem fez o quê?, Mesmo som |
| `numberSelect` | Números 1–4 (palmas) | Palmas nas sílabas |
| `tapGroup` | Toque no cesto (sem drag) | Palavras amigas |
| `letterSelect` | Letras ampliadas | Letras da turma |
| `storyThenObserve` | História em frames + escala 0–3 da professora | Reconto |

### Atividades do catálogo

| Jogo | Código PE | Itens (resumo) |
|---|---|---|
| Jogo das rimas (`rimas`, 8 min) | EF12LP07PE | GATO→PATO, SOL→GOL, LUA→RUA, FADA→NADA, REI→LEI |
| Palmas nas sílabas (`silabas`, 8 min) | EF01LP06PE | CASA(2), SOL(1), JANELA(3), PATO(2), BORBOLETA(4) |
| Reconto com imagens (`reconto`, 10 min) | EF15LP19PE | História do pato; registro 0–3 |
| Quem fez o quê? (`compreensao`, 7 min) | EF15LP03PE | Quem / onde / com o quê |
| Palavras amigas (`vocabulario`, 7 min) | EF01LP15PE | Frutas × brinquedos |
| Mesmo som (`fonologica`, 8 min) | EF01LP09PE | GA, ME, SO |
| Letras da turma (`letras`, 6 min) | EF01LP05PE | CASA→C, PATO→P, LUNA→L, SOL→S |

### Pontuação no app (local, independente do Django)

Itens certo/errado: 0 ou 1. Razão = acertos / n.

| Estrelas (Praticar) | Razão | Rótulo pedagógico |
|---|---|---|
| 5 | ≥ 0,9 | Habilidade demonstrada (≥ 0,8) |
| 4 | ≥ 0,7 | Em desenvolvimento (≥ 0,5) |
| 3 | ≥ 0,5 | Em desenvolvimento |
| 2 | ≥ 0,3 | Necessita maior mediação |
| 1 | abaixo | Necessita maior mediação |

Reconto (observacional): 3 = demonstrada (5★) · 2 = com apoio (4★) · 1 = mediação (2★) · 0 = não observado (1★). Atenção se score ≤ 1.

Modo **Sondagem**: mesma conta interna, **sem** feedback certo/errado na tela da criança.

`PlayerProfile` combina settings do tablet + features do aluno. Sempre `noDrag = true`. Texto ampliado escala 1,28; alvos amplos min. 88 px (senão 64). Legendas e “repetir” ligam também com leitor de tela.

`TtsService` (`flutter_tts`): `pt-BR`, rate 0.42. Desligável em Ajustes.

Plataformas no repo: Android (`br.gov.jucati.mitaka.mitaka_teacher`), Web (PWA), Windows. Sem pastas iOS/macOS/Linux.

---

## 15. Templates e front web

Pasta `templates/` (57 HTMLs). Bases:

- `base.html` — público/login
- `admin_panel/base_admin.html` — gestão + secretaria (sidebar por `nav`)
- `teacher/base_teacher.html` — portal professor
- `family/base_family.html` — família
- `assessment/base.html` — player tela cheia

### Público / auth

- `public/home.html` — pitch do edital
- `registration/login.html` — login + atalhos demo
- `registration/csrf_failure.html`

### Professor

- `home.html`, `classroom_list.html`, `classroom_detail.html`
- `student_profile.html` (abas)
- `evidence_form.html`, `intervention_form.html`
- `planning.html`, `session_result.html`
- `support_plan_form.html`, `support_strategy_form.html`

### Família

- `family/home.html`, `family/child.html`

### Avaliação

- `preview_adapted.html` — montagem automática
- `play.html` — item atual + acessibilidade
- `print_accessible.html` — impressão

### Gestão / Secretaria / adoção

Dashboards, CRUDs genéricos (`form.html`, `confirm_delete.html`, `forbidden.html`), escolas, turmas, estudantes, matrículas, professores, import CSV, matriz, dimensões, alinhamento, instrumentos, itens, templates, indicadores, intervenções, relatórios (estudante/turma/escola/rede), secretaria, comparação, necessidades, drill-down, implantação, formações, uso.

Componente: `components/status_badge.html`.

### Static

- `static/css/app.css` — professora/família (cards, KPIs, tiles)
- `static/css/admin.css` — gestão (sidebar 260 px)
- `static/css/accessibility.css` — skip-link, `:focus-visible`, `a11y-large-text` / `high-contrast` / `large-target` / `reduced-stimulus`, `prefers-reduced-motion`, print
- `static/js/admin.js` — sidebar colapsável (localStorage) + drawer mobile
- `static/pwa/manifest.json` — PWA “Mitaka Edu”, standalone, tema `#0d6e6e`, `lang: pt-BR`
- `static/pwa/sw.js` — cache `mitaka-static-v3`; navegações `no-store`

O `base.html` referencia `icon-192.png` / `icon-512.png` em `/static/pwa/`; no repo esses PNGs ainda podem não estar versionados nessa pasta (o Flutter web tem ícones em `teacher_app/web/icons/`).

---

## 16. Infra, dependências e deploy

### Requirements

`requirements/base.txt`: Django 5, DRF, django-environ, psycopg2, redis, celery, gunicorn, Pillow, WhiteNoise, ReportLab.

`local.txt` e `production.txt` hoje só fazem `-r base.txt` (a diferença está nos **settings**, não nos pacotes).

### Docker (detalhe)

- `Dockerfile`: Python 3.11-slim, `requirements/production.txt`, Gunicorn 2 workers em `:8000`
- `docker/entrypoint.sh`: `migrate` + `collectstatic` + `exec`
- `docker/nginx/default.conf`: `/static/` e `/media/`; proxy `X-Forwarded-*`; `client_max_body_size 10M`
- Sem worker Celery no compose (tarefas eager no local)

### Config Python

- `config/settings/base.py` — comum
- `config/settings/local.py` — DEBUG, static simples (sem hash), Celery eager
- `config/settings/production.py` — `DEBUG=False`, SSL redirect, cookies Secure+Lax, HSTS 1 ano, `X_FRAME_OPTIONS=DENY`, Celery **não** eager, CSRF `edu.innomove.com.br`
- `config/wsgi.py` / `asgi.py` — default **production**; `celery.py` app `mitaka`

`.cpanel.yml` dispara `scripts/cpanel_deploy.sh` no Git deploy do cPanel.

---

## 17. Testes (o que está coberto)

### `apps/core/tests/test_critical.py`

RBAC (professor não vê outra escola; família não entra na gestão), freeze de matriz na sessão, scoring, import CSV, novo ano sem apagar histórico, intervenção sugerida, etc.

### `apps/core/tests/test_challenge_alignment.py`

Home pública cita edital; família só vê a criança vinculada; secretaria abre implantação/uso; login família cai em `/familia/`.

### `apps/accessibility/tests/`

Resolver: barreira ≠ erro; variantes equivalentes; privacidade do perfil; preservação histórica da variante na resposta.

### `apps/reports/tests/`

Geração de relatórios HTML/PDF nos escopos.

Outros apps têm `tests.py` mais leves (accounts, analytics, assessments, schools, interventions, planning, evidences, ai, curriculum).

---

## 18. App `ai` (stub)

Sem models, sem views úteis, sem admin, sem API externa. **Não envia dados de criança para fora.** Arquivo: `apps/ai/services.py`.

| Função | Retorno no MVP |
|---|---|
| `generate_plan` | `{status: not_implemented_ai}` — usar planejamento por regras |
| `generate_student_summary` | idem — usar relatórios HTML |
| `suggest_intervention` | regras locais via `recommend_template_for_result` |
| `analyze_classroom` | placeholder — usar dashboards |

**IA não publica adaptações** sozinha: variantes acessíveis exigem aprovação pedagógica.

---

## 19. Regras de negócio que não podem quebrar

1. **Estudante ≠ matrícula.** Identidade permanente; ano/turma mudam sem apagar histórico.
2. **Só um ano letivo ativo.**
3. **Professor só vê as próprias turmas.** Gestão só a própria escola. Rede vê tudo. Família só o vínculo.
4. **Matriz publicada congela** na sessão de avaliação.
5. **Critérios de scoring vivem no banco** (`ScoringRule`), não em `if` soltos (há fallback só se faltar regra).
6. **Barreira de acessibilidade nunca vira nota baixa.**
7. **Tempo e repetir instrução não reduzem pontuação** (salvo `time_is_construct`, raro).
8. **Professor não edita perfil de acessibilidade** por padrão; vê recursos necessários.
9. **Família não recebe rótulo clínico nem ranking.**
10. **Soft delete** na maior parte dos cadastros; hard delete restrito (e bloqueado se há dependências).
11. **Audit log** em login, import, matrícula, acessibilidade, plano de apoio.
12. **Sem drag-and-drop e sem degradê** na UX de criança/professor.
13. **Uso da rede não serve para punir ou ranquear escolas**; necessidades pedagógicas **não automatizam** decisão.
14. Relatórios PDF trazem rodapé: *documento pedagógico · não constitui diagnóstico clínico*.

---

## 20. O que ainda NÃO está no MVP

- Sincronização offline avançada de respostas (web/Flutter)
- Flutter **conectado** à API Django (hoje demo local)
- Integração com sistemas municipais (matricula oficial, SSO)
- IA externa ou geração automática de itens
- Instrumentos clínicos validados
- Celery/Redis obrigatórios no fluxo síncrono (estão preparados)
- API REST completa de cadastros
- PWA com cache sofisticado (service worker é básico)

Próximos passos naturais (também no README): PDF já existe via ReportLab; offline sync; integrações municipais; IA opcional no `apps/ai`; PostgreSQL + HTTPS + backups em produção.

---

## 21. Roteiro de demonstração (pitch)

1. Abrir `/` → explicar os 8 pontos do edital → Entrar.
2. Login `secretaria` → painel municipal → **Implantação** / **Uso da rede** / **Formação continuada** → indicadores e comparação ética.
3. Login `professora` → Hoje → **Iniciar sondagem** com **Luna** (ver adaptação automática) → jogar → resultado sem penalizar acomodação → registrar evidência **visível à família**.
4. Login `familia` → ver Luna em linguagem simples + dicas para casa (sem nota).
5. Login `coordenador` ou `aee` → intervenções / plano de apoio.
6. Login `gestor` → cadastros da escola, import CSV, relatórios.
7. (Opcional) `cd teacher_app && flutter run` → mesma Luna no tablet, Jogo das rimas, sem degradê/drag.

---

## 22. Índice rápido: “onde fica no código”

| Quero… | Olhar |
|---|---|
| Rotas globais | `config/urls.py` |
| Papéis e menu | `apps/core/permissions.py` |
| Escopo de dados | `apps/accounts/selectors.py` |
| Login e redirect | `apps/accounts/views.py` |
| Cadastro de equipe | `apps/accounts/views_teachers.py` + `forms.py` |
| Portal professor | `apps/accounts/views_teacher.py` + `urls_teacher.py` |
| Portal gestão | `apps/accounts/views_management.py` + `urls_management.py` |
| Secretaria | `apps/analytics/views_secretaria.py` |
| Família / implantação | `apps/adoption/views.py` + `services.py` |
| Resolver acessibilidade | `apps/assessments/services/resolver.py` |
| Sessão / autosave | `apps/assessments/services/session.py` |
| Scoring | `apps/assessments/services/scoring.py` |
| Player web | `apps/assessments/views.py` + `templates/assessment/` |
| Import CSV | `apps/students/services/import_csv.py` |
| Novo ano | `apps/schools/services/school_year.py` |
| PDF | `apps/reports/services/pdf.py` |
| Seed | `apps/core/management/commands/seed_demo.py` |
| Stubs de IA | `apps/ai/services.py` |
| App tablet | `teacher_app/lib/` |

---

## 23. Licença / uso

Projeto MVP para demonstração do desafio de inovação aberta — Jucati/PE. Dados do seed são fictícios. Instrumentos e status são pedagógicos e demonstrativos, não diagnósticos.
