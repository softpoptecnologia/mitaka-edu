import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../data/activity_catalog.dart';
import '../state/app_state.dart';
import '../theme/app_colors.dart';
import '../widgets/common.dart';
import 'activity_prepare_screen.dart';

class ActivityCatalogScreen extends StatelessWidget {
  const ActivityCatalogScreen({super.key, this.standalone = false, this.preselectedStudentId});

  final bool standalone;
  final String? preselectedStudentId;

  @override
  Widget build(BuildContext context) {
    final student = preselectedStudentId == null
        ? null
        : context.watch<AppState>().studentById(preselectedStudentId!);
    final body = ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
      children: [
        if (!standalone) Text('Jogos', style: Theme.of(context).textTheme.headlineMedium),
        if (!standalone) const SizedBox(height: 4),
        Text(
          student == null
              ? 'Sondagens lúdicas com áudio, imagem e toque. Sem arrastar e sem cronômetro.'
              : 'Escolha o jogo para ${student.fullName}. Os apoios entram sozinhos.',
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.muted),
        ),
        const SizedBox(height: 16),
        for (final activity in ActivityCatalog.all) ...[
          InkWell(
            borderRadius: BorderRadius.circular(20),
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => ActivityPrepareScreen(
                  activityId: activity.id,
                  preselectedStudentId: preselectedStudentId,
                ),
              ),
            ),
            child: SectionCard(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
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
                        Text(activity.subtitle, style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.muted)),
                        const SizedBox(height: 6),
                        Text(
                          '${activity.estimatedMinutes} min · ${activity.dimension}',
                          style: Theme.of(context).textTheme.labelLarge?.copyWith(color: accentSolid(activity.accentToken)),
                        ),
                        const SizedBox(height: 8),
                        Wrap(
                          spacing: 6,
                          runSpacing: 6,
                          children: [
                            for (final res in activity.resources.take(4)) ResourceChip(label: res, compact: true),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
        ],
      ],
    );

    if (!standalone) return SafeArea(child: body);
    return Scaffold(
      appBar: AppBar(title: const Text('Escolher atividade')),
      body: body,
    );
  }
}
