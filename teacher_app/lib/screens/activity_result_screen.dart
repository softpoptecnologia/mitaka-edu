import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../state/app_state.dart';
import '../theme/app_colors.dart';
import '../widgets/common.dart';
import 'activity_catalog_screen.dart';
import 'activity_prepare_screen.dart';

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
    final nextPending = state.nextPendingAfter(session.student.id);

    return Scaffold(
      appBar: AppBar(title: const Text('Como foi')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
        children: [
          SectionCard(
            child: Column(
              children: [
                Text(session.activity.emoji, style: const TextStyle(fontSize: 48)),
                const SizedBox(height: 8),
                Text(session.activity.title, style: Theme.of(context).textTheme.headlineSmall),
                Text(
                  session.student.fullName,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.muted),
                ),
                const SizedBox(height: 12),
                if (practice) StarRow(count: session.stars, size: 36),
                const SizedBox(height: 12),
                Text(session.pedagogicalLabel, style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 6),
                Text(
                  session.needsAttention
                      ? 'Vale repetir esta brincadeira em outro momento, com mais apoio.'
                      : 'Siga com as brincadeiras de linguagem desta turma.',
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
                Text(session.activity.skillName, style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: 6),
                Text(
                  session.activity.skillCode,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.muted),
                ),
                const SizedBox(height: 8),
                const Text('Os apoios de acesso (áudio, legendas, toque amplo) não mudam o que a criança demonstrou.'),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Text('Observação da professora', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          TextField(
            controller: _note,
            maxLines: 3,
            decoration: const InputDecoration(
              hintText: 'Como a criança participou? Sem dados clínicos.',
            ),
          ),
          const SizedBox(height: 16),
          if (state.syncing)
            const Padding(
              padding: EdgeInsets.only(bottom: 12),
              child: Text('Enviando para a web Mitaka Edu…', textAlign: TextAlign.center),
            )
          else if (state.lastSyncError != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Text(state.lastSyncError!, textAlign: TextAlign.center, style: const TextStyle(color: Color(0xFFB42318))),
            )
          else if (state.online)
            const Padding(
              padding: EdgeInsets.only(bottom: 12),
              child: Text('Resultado enviado para a web.', textAlign: TextAlign.center),
            ),
          if (!_savedNote)
            FilledButton(
              onPressed: () async {
                await state.updateLastObservation(_note.text);
                if (!context.mounted) return;
                setState(() => _savedNote = true);
              },
              child: const Text('Salvar observação'),
            )
          else
            Text(
              state.online ? 'Observação salva na web.' : 'Observação salva neste aparelho.',
              textAlign: TextAlign.center,
            ),
          const SizedBox(height: 16),
          FilledButton.tonalIcon(
            onPressed: () => Navigator.pushReplacement(
              context,
              MaterialPageRoute(
                builder: (_) => ActivityCatalogScreen(
                  standalone: true,
                  preselectedStudentId: session.student.id,
                ),
              ),
            ),
            icon: const Icon(Icons.replay_rounded),
            label: Text('Fazer outra com ${session.student.fullName.split(' ').first}'),
          ),
          if (nextPending != null) ...[
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: () {
                final activity = state.suggestedActivityFor(nextPending);
                Navigator.pushReplacement(
                  context,
                  MaterialPageRoute(
                    builder: (_) => ActivityPrepareScreen(
                      activityId: activity.id,
                      preselectedStudentId: nextPending.id,
                      initialMode: ActivityMode.survey,
                    ),
                  ),
                );
              },
              icon: const Icon(Icons.arrow_forward_rounded),
              label: Text('Próximo pendente: ${nextPending.fullName.split(' ').first}'),
            ),
          ],
          const SizedBox(height: 10),
          TextButton(
            onPressed: () => Navigator.popUntil(context, (route) => route.isFirst),
            child: const Text('Voltar ao Hoje'),
          ),
        ],
      ),
    );
  }
}
