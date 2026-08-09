import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import '../theme/app_colors.dart';
import '../widgets/common.dart';
import 'classroom_detail_screen.dart';

class ClassroomsScreen extends StatelessWidget {
  const ClassroomsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final rooms = context.watch<AppState>().classrooms;
    return SafeArea(
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
        children: [
          Text('Turmas', style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 4),
          Text(
            'Toque na turma para ver as crianças e iniciar a sondagem.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.muted),
          ),
          const SizedBox(height: 16),
          for (final room in rooms) ...[
            InkWell(
              borderRadius: BorderRadius.circular(20),
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => ClassroomDetailScreen(classroomId: room.id)),
              ),
              child: SectionCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(room.name, style: Theme.of(context).textTheme.titleLarge),
                    Text(room.schoolName, style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.muted)),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        ResourceChip(label: '${room.students.length} estudantes'),
                        if (room.pendingCount > 0) ResourceChip(label: '${room.pendingCount} pendentes'),
                        if (room.attentionCount > 0) ResourceChip(label: '${room.attentionCount} atenção'),
                        if (room.supportCount > 0) ResourceChip(label: '${room.supportCount} com apoio'),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
          ],
        ],
      ),
    );
  }
}
