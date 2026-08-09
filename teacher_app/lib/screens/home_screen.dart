import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../state/app_state.dart';
import '../theme/app_colors.dart';
import '../widgets/brand_mark.dart';
import '../widgets/common.dart';
import 'activity_catalog_screen.dart';
import 'activity_prepare_screen.dart';
import 'classroom_detail_screen.dart';
import 'student_detail_screen.dart';

enum _TodayFilter { all, pending, attention, ok }

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  _TodayFilter _filter = _TodayFilter.all;

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final name = state.user?.displayName.split(' ').first ?? 'professora';
    final queue = switch (_filter) {
      _TodayFilter.all => state.todayQueue,
      _TodayFilter.pending => state.pendingStudents,
      _TodayFilter.attention => state.attentionStudents,
      _TodayFilter.ok => state.okStudents,
    };

    return SafeArea(
      child: RefreshIndicator(
        onRefresh: () async {
          await state.refreshFromServer();
        },
        child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
        children: [
          MitakaHeader(
            title: 'Olá, $name',
            subtitle: state.isDemoApi
                ? 'Dados de demonstração neste aparelho'
                : 'Conectado em ${state.baseUrl.replaceFirst(RegExp(r'^https?://'), '')}',
          ),
          const SizedBox(height: 20),
          Row(
            children: [
              Expanded(
                child: StatCard(
                  label: 'Estudantes',
                  value: '${state.studentCount}',
                  icon: Icons.people_alt_rounded,
                  color: AppColors.brandDark,
                  soft: AppColors.brandSoft,
                  selected: _filter == _TodayFilter.all,
                  onTap: () => setState(() => _filter = _TodayFilter.all),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: StatCard(
                  label: 'Sondagem pendente',
                  value: '${state.pendingCount}',
                  icon: Icons.hourglass_bottom_rounded,
                  color: AppColors.pending,
                  soft: AppColors.pendingSoft,
                  selected: _filter == _TodayFilter.pending,
                  onTap: () => setState(() => _filter = _TodayFilter.pending),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: StatCard(
                  label: 'Atenção',
                  value: '${state.attentionCount}',
                  icon: Icons.flag_rounded,
                  color: AppColors.attention,
                  soft: AppColors.attentionSoft,
                  selected: _filter == _TodayFilter.attention,
                  onTap: () => setState(() => _filter = _TodayFilter.attention),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: StatCard(
                  label: 'Regular',
                  value: '${state.okCount}',
                  icon: Icons.sentiment_satisfied_alt_rounded,
                  color: AppColors.ok,
                  soft: AppColors.okSoft,
                  selected: _filter == _TodayFilter.ok,
                  onTap: () => setState(() => _filter = _TodayFilter.ok),
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Text(
            _filter == _TodayFilter.all ? 'Comece por aqui' : 'Filtrados',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 4),
          Text(
            _filter == _TodayFilter.pending
                ? 'Crianças que ainda não fizeram a sondagem lúdica.'
                : _filter == _TodayFilter.attention
                    ? 'Vale observar de novo e registrar como foi.'
                    : 'Toque em Iniciar para jogar com a criança.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.muted),
          ),
          const SizedBox(height: 12),
          if (queue.isEmpty)
            SectionCard(
              child: Text(
                _filter == _TodayFilter.ok
                    ? 'Nenhuma criança neste recorte. Veja as pendências ou as turmas.'
                    : 'Nada pendente neste recorte. Você pode abrir as turmas ou ver todos os jogos.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            )
          else
            for (final student in queue) ...[
              _TodayTaskCard(student: student),
              const SizedBox(height: 10),
            ],
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const ActivityCatalogScreen(standalone: true)),
            ),
            icon: const Icon(Icons.extension_outlined),
            label: const Text('Ver todos os jogos'),
          ),
          const SizedBox(height: 20),
          Text('Minhas turmas', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          for (final room in state.classrooms) ...[
            InkWell(
              borderRadius: BorderRadius.circular(20),
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => ClassroomDetailScreen(classroomId: room.id)),
              ),
              child: SectionCard(
                child: Row(
                  children: [
                    Container(
                      width: 48,
                      height: 48,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: AppColors.brandSoft,
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: const Icon(Icons.school_rounded, color: AppColors.brandDark),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(room.name, style: Theme.of(context).textTheme.titleMedium),
                          Text(
                            '${room.students.length} crianças · ${room.pendingCount} pendente${room.pendingCount == 1 ? '' : 's'}',
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.muted),
                          ),
                        ],
                      ),
                    ),
                    const Icon(Icons.chevron_right_rounded, color: AppColors.muted),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 10),
          ],
        ],
        ),
      ),
    );
  }
}

class _TodayTaskCard extends StatelessWidget {
  const _TodayTaskCard({required this.student});

  final Student student;

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final room = state.classroomById(student.classroomId);
    final activity = state.suggestedActivityFor(student);
    final pending = student.status == StudentStatus.pending;
    return SectionCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          InkWell(
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => StudentDetailScreen(studentId: student.id)),
            ),
            child: Row(
              children: [
                StudentAvatar(student: student, size: 52),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(student.fullName, style: Theme.of(context).textTheme.titleMedium),
                      Text(
                        room?.name ?? '',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.muted),
                      ),
                      const SizedBox(height: 6),
                      Wrap(
                        spacing: 6,
                        runSpacing: 6,
                        children: [
                          StatusChip(status: student.status),
                          ResourceChip(label: activity.title, compact: true),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Text(
            pending
                ? 'Ainda precisa da sondagem lúdica. Sugerido: ${activity.title}.'
                : 'Bom momento para observar de novo com ${activity.title}.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.muted),
          ),
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => ActivityPrepareScreen(
                  activityId: activity.id,
                  preselectedStudentId: student.id,
                  initialMode: pending ? ActivityMode.survey : ActivityMode.practice,
                ),
              ),
            ),
            icon: const Icon(Icons.play_arrow_rounded),
            label: Text(pending ? 'Iniciar sondagem' : 'Iniciar'),
          ),
        ],
      ),
    );
  }
}
