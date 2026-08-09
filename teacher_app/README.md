# Mitaka Atividades — app do professor

App Flutter para o professor aplicar **atividades lúdicas e gamificadas** de leitura e escrita (Currículo PE / BNCC), com **áudio, imagem e recursos de acessibilidade** conforme a necessidade de cada estudante.

No edital municipal: cobre o **item 1** (sondagem lúdica, faixa etária) e o **item 7** (tablet/celular na escola). A web cobre planejamento, evidências, painéis, família, formação e implantação.

Pasta: `teacher_app/` (separada do Django web).

## Princípios de UX

- Fácil: poucos toques, botões grandes, linguagem clara. O Início (**Hoje**) mostra a fila do dia.
- Atrativo sem excesso: ilustrações sólidas, estrelas no modo praticar.
- **Sem degradês** (gradientes prejudicam contraste, leitura e crianças com hipersensibilidade visual).
- **Sem arrastar e soltar** e **sem cronômetro**.
- Acomodação de acesso **não reduz** o status pedagógico.

## Atividades

| Jogo | Habilidade | Recursos |
|---|---|---|
| Jogo das rimas | EF12LP07PE | Áudio, imagem, legendas, Libras |
| Palmas nas sílabas | EF01LP06PE | Áudio, imagem, toque amplo |
| Reconto com imagens | EF15LP19PE | História em áudio + imagens + observação |
| Quem fez o quê? | EF15LP03PE | Escuta, legendas, escolha por imagem |
| Palavras amigas | EF01LP15PE | Agrupar por toque (sem arrastar) |
| Mesmo som | EF01LP09PE | Áudio do som inicial + imagem |
| Letras da turma | EF01LP05PE | Letra ampliada + áudio |

Cada item pode mostrar: voz (TTS), legendas, dica em Libras, passo a passo, alvos ampliados, texto grande e alto contraste — conforme o perfil do aluno.

## Como rodar

```bash
cd teacher_app
flutter pub get
flutter run
```

No navegador: `flutter run -d chrome`  
No Windows: `flutter run -d windows`

## Acesso demo

**Só professora.** AEE, gestor, coordenador, secretaria e família **não entram no app** — usam a web (`/professor/`, `/gestao/`, `/secretaria/`, `/familia/`).

Senha: `demo1234`

| Usuário | Turmas |
|---|---|
| `professora` | Maria Inez (Inf. V A/B), Eliel Peixoto (Inf. IV A), Ananias (Inf. V A) |
| `professor2` | Tia Noêmia (Inf. V A) e Albino Moreira (1º Ano A) |

Experimente **Luna** (texto ampliado + alto contraste) ou **Theo** (áudio / leitor de tela).

## Fluxo

1. Entrar → **Hoje** (o que fazer agora, com quem)  
2. **Iniciar sondagem** na criança pendente (ou abrir Turma)  
3. Praticar (estrelas) ou Sondagem (sem certo/errado na tela da criança)  
4. Jogar → resultado pedagógico + observação → próxima pendente  

Em **Ajustes** (e no login) escolha o servidor **Web** (`https://edu.innomove.com.br`) ou **Local** (`http://127.0.0.1:8000` no PC, `http://10.0.2.2:8000` no emulador Android). O app entra com o usuário **da professora** (o mesmo da web) e carrega turmas, crianças, status e apoios. A sondagem lúdica grava evidência (e atualiza a habilidade) no Django.

Com o Django no ar: `python manage.py migrate` (cria a tabela `authtoken`) e `python manage.py runserver`. Sem o migrate, o login do app quebra. Seed: `professora` / `professor2` · senha `demo1234`.

O servidor **Web** (`edu.innomove.com.br`) só aceita o app depois de publicar esse código. Até lá, use **Local**.
