# Mitaka Edu

Plataforma educacional de acompanhamento contínuo das habilidades precursoras e iniciais da leitura e escrita, desenvolvida como MVP para o desafio de inovação aberta da Secretaria Municipal de Educação de Jucati/PE.

**Documentação completa (raio-X do sistema, fluxos e “como fazer cada coisa”):** [DOCUMENTACAO.md](DOCUMENTACAO.md)

## Objetivo

Transformar o ciclo pedagógico fragmentado em uma rotina digital integrada:

**Diagnosticar → Analisar → Planejar → Intervir → Registrar evidências → Acompanhar → Reavaliar**

A complexidade pedagógica fica no sistema (matriz, critérios, instrumentos). O professor encontra automaticamente turmas, pendências, resultados e intervenções sugeridas. A Secretaria monitora a rede; a família acompanha a criança sem notas nem rótulos clínicos.

**Alinhamento ao edital (8 pontos):** sondagem lúdica · planejamento · evidências · painéis (estudante/turma/escola/rede) · intervenção e formação continuada · menos retrabalho · multi-dispositivo (web, PWA, Flutter) · implantação, suporte e monitoramento de uso.

Página pública: `/` (deslogado). Demo família: `familia` / `demo1234`.

## Arquitetura

- **Backend:** Python, Django, Django REST Framework (API parcial)
- **Banco:** SQLite (local) ou PostgreSQL (Docker)
- **Front gestão:** Django Templates + Bootstrap 5 (layout AdminLTE-like)
- **Front professor (web):** Templates + Bootstrap 5 + HTMX
- **App professor (Flutter):** `teacher_app/` — atividades lúdicas gamificadas (áudio, imagem, acessibilidade), sem degradês
- **Avaliação web:** interface tela cheia lúdica
- **Infra:** Docker Compose, Nginx, Gunicorn, Redis, Celery preparado
- **PWA:** manifest + service worker básico

## Requisitos

Python 3.11+, pip. Para stack completa: Docker e Docker Compose.

## Instalação local (SQLite)

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements/local.txt
copy .env.example .env   # ou cp .env.example .env
# No .env local, use: DATABASE_URL=sqlite:///db.sqlite3

python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Acesse: http://127.0.0.1:8000/

## Docker

```bash
cp .env.example .env
# Ajuste DATABASE_URL para postgres://mitaka:mitaka@db:5432/mitaka
docker compose up --build
```

Aplicação via Nginx: http://localhost:8080/

## Variáveis de ambiente

Veja `.env.example` (local) e `.env.production.example` (cPanel / produção):

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`
- `REDIS_URL`
- `CELERY_BROKER_URL`

**Nunca versione o arquivo `.env` com segredos reais.** No servidor, copie `.env.production.example` para `.env` na raiz do app.

## Publicar no cPanel (produção)

Atualizar o GitHub **não** atualiza o site sozinho. No servidor:

1. **Git Version Control** → *Pull or Deploy* (ou *Update from Remote* + *Deploy*).
2. No **Terminal** do cPanel, na pasta do app Python:

```bash
source ~/virtualenv/edu.innomove.com.br/3.11/bin/activate
cd ~/edu.innomove.com.br
git pull
bash scripts/cpanel_deploy.sh
```

O script roda `migrate`, `collectstatic` e `touch tmp/restart.txt` (recarrega o Passenger). Sem isso o WhiteNoise continua servindo o CSS antigo.

3. No navegador: `Ctrl + F5` (o PWA pode guardar cache velho).

Se o Git do cPanel estiver em `~/repositories/` e o app em outra pasta, o *Deploy* precisa copiar/atualizar a pasta do Python App — não só o repositório.

## Migrations e superusuário

```bash
python manage.py migrate
python manage.py createsuperuser
```

O `seed_demo` já cria um admin: usuário `admin` / senha `demo1234`.

## Seed demonstrativo

```bash
python manage.py seed_demo
```

Cria município Jucati, 3 escolas, 6+ turmas, ~30 estudantes fictícios, matriz pedagógica, instrumentos, respostas, intervenções, evidências textuais, **perfis de acessibilidade (estudantes A–E)**, variantes acessíveis e plano de apoio.

## Usuários demonstrativos

Senha de todos: `demo1234`

| Usuário | Perfil |
|---|---|
| `admin` | Superadmin |
| `secretaria` | Secretaria Municipal |
| `tecnico` | Técnico pedagógico |
| `gestor` | Gestor escolar |
| `coordenador` | Coordenador |
| `aee` | Atendimento Educacional Especializado |
| `professora` | Professora (turmas Infantil V A/B) |
| `professor2` | Professor |
| `familia` | Família / responsável (Luna Ferreira) |

## Acessibilidade e educação inclusiva

A plataforma prioriza **necessidades funcionais de acesso** (não diagnósticos). App `accessibility` + motor `AccessibilityAssessmentResolver`:

- perfil de recursos (texto ampliado, leitor de tela, sem drag, etc.);
- variantes `EQUIVALENT` / `ALTERNATIVE` versionadas;
- barreira de acessibilidade **nunca** vira baixo desempenho (`NOT_APPLICABLE` / `REQUIRES_ALTERNATIVE_INSTRUMENT`);
- professor vê “recursos necessários”; AEE/coordenação edita perfil e plano de apoio;
- indicadores da secretaria são agregados (sem rotulagem discriminatória).

**Demo / pitch inclusivo:** login `professora` → turma → Luna (ou estudante com recursos) → aba Avaliações → **Preparar** → ver montagem automática → Iniciar → resultado registra variantes sem reduzir pontuação por acomodação.

## Relatórios PDF

Padrão visual único (cabeçalho Mitaka Edu, tabelas, rodapé pedagógico):

- estudante, turma, escola e rede
- tela / impressão / `?formato=pdf`
- botões no perfil do estudante, na turma e na secretaria

```bash
# Ex.: /gestao/relatorios/estudante/<id>/?formato=pdf
```

## Testes

```bash
python manage.py test apps.core.tests apps.accessibility.tests apps.reports.tests apps.interventions.tests
```

Cobertura crítica: RBAC, longitudinalidade, freeze de matriz, scoring, CSV, **resolver de acessibilidade**, privacidade de perfil e preservação histórica de variantes.

## Estrutura dos apps

- `accounts` — usuários, roles, portal professor/gestão
- `schools` — município, escolas, anos, turmas
- `students` — estudante permanente + matrículas + import CSV
- `curriculum` — matriz pedagógica versionada
- `assessments` — instrumentos, variantes acessíveis, sessões, scoring
- `accessibility` — categorias/features, perfil do estudante, plano de apoio
- `evidences` — evidências
- `interventions` — templates e intervenções
- `planning` — planejamento assistido
- `analytics` — indicadores e dashboards da secretaria
- `reports` — relatórios HTML
- `adoption` — implantação, formação continuada, monitoramento de uso, portal da família
- `ai` — stubs preparados (MVP sem IA externa; IA não publica adaptações)
- `core` — audit log, mixins, seed

## Fluxo principal (pitch)

1. Abrir `/` (página pública alinhada ao edital) → Entrar  
2. Login `secretaria` → painel municipal → **Implantação** / **Uso da rede** / **Formação continuada**  
3. Login `professora` → turma → Luna → **Preparar** sondagem → evidência compartilhada com a família  
4. Login `familia` → ver Luna em linguagem simples + dicas para casa (sem nota)  
5. Login `coordenador` → intervenções e formação  
6. Voltar à Secretaria → indicadores e cobertura de uso  

## Alinhamento curricular

A matriz pedagógica do MVP está alinhada ao **Currículo de Pernambuco** e à **BNCC** (Língua Portuguesa — Anos Iniciais), na perspectiva de **alfabetizar letrando**:

- códigos PE (ex.: `EF01LP06PE`, `EF12LP07PE`, `EF15LP19PE`);
- consciência fonológica em contextos de uso (parlendas, cantigas, listas);
- ênfase lúdica na transição Educação Infantil → Anos Iniciais;
- página **Alinhamento PE / Currículo PE** na gestão e na Secretaria.

As sondagens são **demonstrativas** e não clínicas.

- Sem sincronização offline avançada de respostas
- PDF real não implementado (HTML print-ready)
- Celery/Redis preparados, não obrigatórios no fluxo síncrono
- Instrumentos são **demonstrativos**, não clínicos/validados
- Sem integração real com sistemas municipais ou IA externa

## App Flutter do professor (`teacher_app/`)

Atividades lúdicas para tablet/celular, alinhadas à matriz PE/BNCC:

```bash
cd teacher_app
flutter pub get
flutter run
```

Login demo: `professora` / `demo1234`. Ver `teacher_app/README.md`.

## Próximos passos

- Exportação PDF
- Offline sync controlado para tablets
- Integrações municipais
- Camada de IA local/privada opcional (apps/ai já preparado)
- PostgreSQL em produção com HTTPS e backups

## Licença / uso

Projeto MVP para demonstração do desafio de inovação aberta — Jucati/PE.
