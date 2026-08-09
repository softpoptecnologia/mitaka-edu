import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../state/app_state.dart';
import '../theme/app_colors.dart';
import '../widgets/common.dart';

class ActivityResultScreen extends StatefulWidget {
  const ActivityResultScreen({super.key});

  @override
  State<ActivityResultScreen> createState() => _ActivityResultScreenState();
}

class _ActivityResultScreenState extends State<ActivityResultScreen> {
  final _note = TextEditingController();
  bool _savedNote = false;

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    if (state.sessions.isEmpty) {
      return const Scaffold(body: Center(child: Text('Sem resultado')));
    }
    final session = state.sessions.first;
    final practice = session.mode == ActivityMode.practice;

    return Scaffold(
      appBar: AppBar(title: const Text('Resultado')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
        children: [
          SectionCard(
            child: Column(
              children: [
                Text(session.activity.emoji, style: const TextStyle(fontSize: 48)),
                const SizedBox(height: 8),
                Text(session.activity.title, style: Theme.of(context).textTheme.headlineSmall),
                Text(session.student.fullName, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.muted)),
                const SizedBox(height: 12),
                if (practice) StarRow(count: session.stars, size: 36),
                const SizedBox(height: 12),
                Text(session.pedagogicalLabel, style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 6),
                Text(
                  session.needsAttention
                      ? 'Sugestão: planejar mediação lúdica nesta habilidade.'
                      : 'Acompanhamento regular. Continue as práticas de linguagem.',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.muted),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          SectionCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('${session.activity.skillCode} — ${session.activity.skillName}', style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: 8),
                const Text(
                  'Recursos de acessibilidade não reduzem o desempenho. '
                  'O que mudou foi só o acesso (áudio, imagem, alvo amplo, legendas…).',
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Text('Observação pedagógica', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          TextField(
            controller: _note,
            maxLines: 3,
            decoration: const InputDecoration(
              hintText: 'Como a criança participou? Sem dados clínicos.',
            ),
          ),
          const SizedBox(height: 16),
          if (!_savedNote)
            FilledButton(
              onPressed: () {
                state.updateLastObservation(_note.text);
                setState(() => _savedNote = true);
              },
              child: const Text('Salvar observação'),
            )
          else
            const Text('Observação salva neste aparelho.', textAlign: TextAlign.center),
          const SizedBox(height: 12),
          OutlinedButton(
            onPressed: () => Navigator.popUntil(context, (route) => route.isFirst),
            child: const Text('Voltar ao início'),
          ),
        ],
      ),
    );
  }
}
