import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../data/activity_catalog.dart';
import '../models/models.dart';
import '../state/app_state.dart';
import '../theme/app_colors.dart';
import '../widgets/common.dart';
import 'activity_player_screen.dart';

class ActivityPrepareScreen extends StatefulWidget {
  const ActivityPrepareScreen({super.key, required this.activityId, this.preselectedStudentId});

  final String activityId;
  final String? preselectedStudentId;

  @override
  State<ActivityPrepareScreen> createState() => _ActivityPrepareScreenState();
}

class _ActivityPrepareScreenState extends State<ActivityPrepareScreen> {
  String? studentId;
  ActivityMode mode = ActivityMode.practice;

  @override
  void initState() {
    super.initState();
    studentId = widget.preselectedStudentId;
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final activity = ActivityCatalog.byId(widget.activityId);
    final students = state.classrooms.expand((c) => c.students).toList();
    final student = studentId == null ? null : state.studentById(studentId!);
    final profile = student == null ? null : state.profileFor(student);
    final applied = <String>[];
    if (student != null) {
      applied.addAll(student.features.map((c) => AccessibilityFeature.byCode(c).label));
      applied.add('Sem arrastar');
      applied.add('Sem cronômetro');
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Preparar atividade')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
        children: [
          SectionCard(
            child: Row(
              children: [
                Container(
                  width: 64,
                  height: 64,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: accentSoft(activity.accentToken),
                    borderRadius: BorderRadius.circular(18),
                  ),
                  child: Text(activity.emoji, style: const TextStyle(fontSize: 30)),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(activity.title, style: Theme.of(context).textTheme.titleLarge),
                      Text(activity.skillCode, style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.muted)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Text(activity.description, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 16),
          Text('Estudante', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          SectionCard(
            padding: EdgeInsets.zero,
            child: ListTile(
              leading: student == null ? const Icon(Icons.person_search_rounded) : StudentAvatar(student: student),
              title: Text(student?.fullName ?? 'Escolher estudante'),
              subtitle: Text(
                student == null
                    ? 'Toque para selecionar'
                    : (state.classroomById(student.classroomId)?.name ?? ''),
              ),
              trailing: const Icon(Icons.expand_more_rounded),
              onTap: () async {
                final chosen = await showModalBottomSheet<String>(
                  context: context,
                  showDragHandle: true,
                  builder: (ctx) => ListView(
                    children: [
                      const ListTile(title: Text('Quem vai jogar?')),
                      for (final s in students)
                        ListTile(
                          leading: StudentAvatar(student: s),
                          title: Text(s.fullName),
                          subtitle: Wrap(
                            spacing: 6,
                            children: [
                              StatusChip(status: s.status),
                              if (s.hasSupport) const ResourceChip(label: 'Recursos', compact: true),
                            ],
                          ),
                          onTap: () => Navigator.pop(ctx, s.id),
                        ),
                    ],
                  ),
                );
                if (chosen != null) setState(() => studentId = chosen);
              },
            ),
          ),
          const SizedBox(height: 16),
          Text('Como jogar', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: _ModeCard(
                  selected: mode == ActivityMode.practice,
                  title: 'Praticar',
                  subtitle: 'Estrelas e incentivo',
                  icon: Icons.sports_esports_rounded,
                  onTap: () => setState(() => mode = ActivityMode.practice),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _ModeCard(
                  selected: mode == ActivityMode.survey,
                  title: 'Sondagem',
                  subtitle: 'Sem certo/errado na tela',
                  icon: Icons.fact_check_outlined,
                  onTap: () => setState(() => mode = ActivityMode.survey),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text('O app vai adaptar', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          SectionCard(
            child: student == null
                ? Text(
                    'Escolha o estudante para ver os recursos (áudio, imagem, texto ampliado, legendas, Libras…).',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.muted),
                  )
                : Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          for (final label in applied.toSet()) ResourceChip(label: label),
                        ],
                      ),
                      if (profile?.libras == true) ...[
                        const SizedBox(height: 12),
                        const Text('Dica em Libras aparece no topo de cada item.'),
                      ],
                      if (profile?.captions == true) ...[
                        const SizedBox(height: 8),
                        const Text('Legendas do áudio ficam visíveis o tempo todo.'),
                      ],
                    ],
                  ),
          ),
          const SizedBox(height: 20),
          FilledButton.icon(
            onPressed: student == null
                ? null
                : () {
                    state.startSession(student: student, activity: activity, mode: mode);
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => const ActivityPlayerScreen()),
                    );
                  },
            icon: const Icon(Icons.play_arrow_rounded),
            label: const Text('Iniciar com a criança'),
          ),
        ],
      ),
    );
  }
}

class _ModeCard extends StatelessWidget {
  const _ModeCard({
    required this.selected,
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.onTap,
  });

  final bool selected;
  final String title;
  final String subtitle;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(20),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: selected ? AppColors.brandSoft : Theme.of(context).cardTheme.color,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: selected ? AppColors.brand : Theme.of(context).dividerColor,
            width: selected ? 2 : 1,
          ),
        ),
        child: Column(
          children: [
            Icon(icon, color: selected ? AppColors.brand : AppColors.muted),
            const SizedBox(height: 8),
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            Text(subtitle, textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.muted)),
          ],
        ),
      ),
    );
  }
}
