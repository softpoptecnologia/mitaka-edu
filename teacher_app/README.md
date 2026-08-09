# Mitaka Atividades — app do professor

App Flutter para o professor aplicar **atividades lúdicas e gamificadas** de leitura e escrita (Currículo PE / BNCC), com **áudio, imagem e recursos de acessibilidade** conforme a necessidade de cada estudante.

No edital municipal: cobre o **item 1** (sondagem lúdica, faixa etária) e o **item 7** (tablet/celular na escola). A web cobre planejamento, evidências, painéis, família, formação e implantação.

Pasta: `teacher_app/` (separada do Django web).

## Princípios de UX

- Fácil: poucos toques, botões grandes, linguagem clara.
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

Senha: `demo1234`

| Usuário | Turmas |
|---|---|
| `professora` | Infantil V A/B (Sol Nascente) e turmas Horizonte |
| `professor2` | Estrela do Saber |

Experimente **Luna** (texto ampliado + alto contraste) ou **Theo** (áudio / leitor de tela).

## Fluxo

1. Entrar → Início  
2. Turma ou estudante → ver recursos necessários  
3. Atividades → preparar (o app monta as adaptações)  
4. **Praticar** (estrelas) ou **Sondagem** (sem certo/errado na tela da criança)  
5. Resultado pedagógico + observação  

Os dados desta versão são **demonstrativos locais** (alinhados ao seed do Mitaka Edu). A integração com a API Django pode ser o próximo passo.
