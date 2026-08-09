import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../state/app_state.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../widgets/common.dart';
import 'activity_result_screen.dart';

class ActivityPlayerScreen extends StatefulWidget {
  const ActivityPlayerScreen({super.key});

  @override
  State<ActivityPlayerScreen> createState() => _ActivityPlayerScreenState();
}

class _ActivityPlayerScreenState extends State<ActivityPlayerScreen> {
  String? _selectedId;
  bool _locked = false;
  String? _feedback;
  bool _feedbackOk = false;
  int _storyIndex = 0;
  bool _storyDone = false;
  bool _objectTouched = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _speakIfNeeded());
  }

  Future<void> _speakIfNeeded() async {
    final state = context.read<AppState>();
    final session = state.activeSession;
    if (session == null) return;
    final profile = state.profileFor(session.student);
    if (profile.ttsEnabled) await state.speakCurrent();
  }

  Future<void> _choose(ActivityChoice choice) async {
    if (_locked) return;
    final state = context.read<AppState>();
    final session = state.activeSession;
    if (session == null) return;
    final profile = state.profileFor(session.student);
    setState(() {
      _selectedId = choice.id;
      _locked = true;
    });
    state.recordChoice(choice);
    if (profile.ttsEnabled) {
      await state.speak(choice.audioText ?? choice.label);
    }

    if (session.mode == ActivityMode.practice && session.activity.items.first.layout != PromptLayout.storyThenObserve) {
      setState(() {
        _feedbackOk = choice.isCorrect;
        _feedback = choice.isCorrect ? 'Mandou bem!' : 'Vamos seguir juntos.';
      });
      await Future<void>.delayed(Duration(milliseconds: profile.reducedMotion ? 400 : 900));
    } else {
      await Future<void>.delayed(Duration(milliseconds: profile.reducedMotion ? 200 : 500));
    }
    if (!mounted) return;
    _advance();
  }

  void _advance() {
    final state = context.read<AppState>();
    setState(() {
      _selectedId = null;
      _locked = false;
      _feedback = null;
      _storyIndex = 0;
      _storyDone = false;
      _objectTouched = false;
    });
    final hasMore = state.nextItem();
    if (!hasMore) {
      state.completeSession();
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const ActivityResultScreen()),
      );
      return;
    }
    _speakIfNeeded();
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final session = state.activeSession;
    if (session == null) {
      return const Scaffold(body: Center(child: Text('Nenhuma atividade em andamento')));
    }
    final profile = state.profileFor(session.student);
    final item = state.currentItem!;
    final prompt = profile.shortInstructions ? item.promptShort : item.prompt;

    return Theme(
      data: AppTheme.light(highContrast: profile.highContrast, textScale: profile.textScale),
      child: Builder(
        builder: (context) {
          final theme = Theme.of(context);
          return Scaffold(
            backgroundColor: profile.highContrast ? AppColors.highContrastBg : AppColors.cream,
            body: SafeArea(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                child: Column(
                  children: [
                    Row(
                      children: [
                        IconButton(
                          tooltip: 'Encerrar',
                          onPressed: () async {
                            final leave = await showDialog<bool>(
                              context: context,
                              builder: (ctx) => AlertDialog(
                                title: const Text('Encerrar atividade?'),
                                content: const Text(
                                  'A criança ainda não terminou. Nesta versão demo, o que já foi feito não fica salvo.',
                                ),
                                actions: [
                                  TextButton(
                                    onPressed: () => Navigator.pop(ctx, false),
                                    child: const Text('Continuar jogando'),
                                  ),
                                  FilledButton(
                                    onPressed: () => Navigator.pop(ctx, true),
                                    child: const Text('Encerrar'),
                                  ),
                                ],
                              ),
                            );
                            if (leave == true && context.mounted) {
                              context.read<AppState>().abandonSession();
                              Navigator.pop(context);
                            }
                          },
                          icon: const Icon(Icons.close_rounded),
                        ),
                        Expanded(
                          child: Text(
                            session.student.fullName,
                            textAlign: TextAlign.center,
                            style: theme.textTheme.titleSmall?.copyWith(color: AppColors.muted),
                          ),
                        ),
                        Text(
                          '${state.activeIndex + 1}/${session.activity.items.length}',
                          style: theme.textTheme.titleSmall,
                        ),
                      ],
                    ),
                    ProgressDots(total: session.activity.items.length, current: state.activeIndex),
                    const SizedBox(height: 8),
                    if (state.showSteps && profile.stepByStep)
                      Expanded(child: _StepsCard(item: item, onContinue: () {
                        state.dismissSteps();
                        _speakIfNeeded();
                      }))
                    else ...[
                      if (profile.libras && item.librasHint != null)
                        _InfoBanner(title: 'Libras', text: item.librasHint!, color: AppColors.grape, soft: AppColors.grapeSoft),
                      if (profile.visualInstruction)
                        _InfoBanner(
                          title: 'Como fazer',
                          text: '1. Ouça  2. Olhe  3. Toque na resposta',
                          color: AppColors.sky,
                          soft: AppColors.skySoft,
                        ),
                      const SizedBox(height: 8),
                      Wrap(
                        alignment: WrapAlignment.center,
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          ListenButton(
                            large: profile.repeatInstructions || profile.largeTarget,
                            onPressed: () => state.speakCurrent(),
                          ),
                          if (profile.repeatInstructions)
                            ListenButton(
                              label: 'De novo',
                              large: profile.largeTarget,
                              onPressed: () => state.speakCurrent(),
                            ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Expanded(
                        child: item.layout == PromptLayout.storyThenObserve
                            ? _StoryThenObserve(
                                item: item,
                                profile: profile,
                                storyDone: _storyDone,
                                storyIndex: _storyIndex,
                                selectedId: _selectedId,
                                onPlayStory: () => state.speak(item.audioText),
                                onFrame: (i) {
                                  setState(() => _storyIndex = i);
                                  state.speak(item.story[i].audioText);
                                },
                                onStoryDone: () => setState(() => _storyDone = true),
                                onChoose: _choose,
                              )
                            : item.layout == PromptLayout.tapGroup
                                ? _TapGroupPlay(
                                    item: item,
                                    prompt: prompt,
                                    profile: profile,
                                    objectTouched: _objectTouched,
                                    selectedId: _selectedId,
                                    onTouchObject: () {
                                      setState(() => _objectTouched = true);
                                      state.speak(item.audioText);
                                    },
                                    onChoose: _choose,
                                  )
                                : _ChoiceItem(
                                    item: item,
                                    prompt: prompt,
                                    profile: profile,
                                    selectedId: _selectedId,
                                    reducedStimulus: profile.reducedStimulus,
                                    onChoose: _choose,
                                  ),
                      ),
                      if (profile.captions) ...[
                        const SizedBox(height: 8),
                        CaptionBar(text: item.caption),
                      ],
                      if (_feedback != null) ...[
                        const SizedBox(height: 8),
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: _feedbackOk ? AppColors.okSoft : AppColors.sunSoft,
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(
                                _feedbackOk ? Icons.star_rounded : Icons.favorite_rounded,
                                color: _feedbackOk ? AppColors.sun : AppColors.coral,
                              ),
                              const SizedBox(width: 8),
                              Text(_feedback!, style: theme.textTheme.titleMedium),
                            ],
                          ),
                        ),
                      ],
                    ],
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _InfoBanner extends StatelessWidget {
  const _InfoBanner({required this.title, required this.text, required this.color, required this.soft});

  final String title;
  final String text;
  final Color color;
  final Color soft;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Theme.of(context).brightness == Brightness.dark ? AppColors.highContrastSoft : soft,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: TextStyle(color: color, fontWeight: FontWeight.w800)),
          Text(text, style: Theme.of(context).textTheme.bodyMedium),
        ],
      ),
    );
  }
}

class _StepsCard extends StatelessWidget {
  const _StepsCard({required this.item, required this.onContinue});

  final ActivityItem item;
  final VoidCallback onContinue;

  @override
  Widget build(BuildContext context) {
    return SectionCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('Vamos juntos, passo a passo', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 16),
          for (var i = 0; i < item.steps.length; i++) ...[
            Row(
              children: [
                CircleAvatar(
                  backgroundColor: AppColors.brand,
                  foregroundColor: Colors.white,
                  child: Text('${i + 1}', style: const TextStyle(fontWeight: FontWeight.w800)),
                ),
                const SizedBox(width: 12),
                Expanded(child: Text(item.steps[i], style: Theme.of(context).textTheme.titleMedium)),
              ],
            ),
            const SizedBox(height: 12),
          ],
          const Spacer(),
          FilledButton(onPressed: onContinue, child: const Text('Começar')),
        ],
      ),
    );
  }
}

class _TapGroupPlay extends StatelessWidget {
  const _TapGroupPlay({
    required this.item,
    required this.prompt,
    required this.profile,
    required this.objectTouched,
    required this.selectedId,
    required this.onTouchObject,
    required this.onChoose,
  });

  final ActivityItem item;
  final String prompt;
  final PlayerProfile profile;
  final bool objectTouched;
  final String? selectedId;
  final VoidCallback onTouchObject;
  final Future<void> Function(ActivityChoice) onChoose;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(prompt, textAlign: TextAlign.center, style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 8),
        Text(
          objectTouched ? 'Agora toque no cesto certo.' : 'Primeiro toque na imagem.',
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(color: AppColors.muted),
        ),
        const SizedBox(height: 16),
        Semantics(
          button: true,
          label: item.imageAlt ?? item.emoji ?? item.promptShort,
          child: Material(
            color: objectTouched ? AppColors.brandSoft : AppColors.surface,
            borderRadius: BorderRadius.circular(28),
            child: InkWell(
              borderRadius: BorderRadius.circular(28),
              onTap: objectTouched ? null : onTouchObject,
              child: Ink(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(vertical: 20),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(28),
                  border: Border.all(
                    color: objectTouched ? AppColors.brand : AppColors.line,
                    width: objectTouched ? 4 : 2,
                  ),
                ),
                child: Column(
                  children: [
                    Text(item.emoji ?? '🧺', style: TextStyle(fontSize: profile.largeText ? 88 : 72)),
                    const SizedBox(height: 8),
                    Text(
                      objectTouched ? 'Escolhida' : 'Toque aqui',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: 16),
        Expanded(
          child: IgnorePointer(
            ignoring: !objectTouched,
            child: Opacity(
              opacity: objectTouched ? 1 : 0.45,
              child: Row(
                children: [
                  for (var i = 0; i < item.choices.length; i++) ...[
                    if (i > 0) const SizedBox(width: 12),
                    Expanded(
                      child: _ChoiceCard(
                        choice: item.choices[i],
                        selected: selectedId == item.choices[i].id,
                        minHeight: profile.targetMin + 24,
                        largeText: profile.largeText,
                        letterStyle: false,
                        onTap: () => onChoose(item.choices[i]),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _ChoiceItem extends StatelessWidget {
  const _ChoiceItem({
    required this.item,
    required this.prompt,
    required this.profile,
    required this.selectedId,
    required this.reducedStimulus,
    required this.onChoose,
  });

  final ActivityItem item;
  final String prompt;
  final PlayerProfile profile;
  final String? selectedId;
  final bool reducedStimulus;
  final Future<void> Function(ActivityChoice) onChoose;

  @override
  Widget build(BuildContext context) {
    final showEmoji = !reducedStimulus || profile.visualInstruction;
    return Column(
      children: [
        if (showEmoji && item.emoji != null)
          Text(item.emoji!, style: TextStyle(fontSize: profile.largeText ? 72 : 56)),
        const SizedBox(height: 8),
        Text(prompt, textAlign: TextAlign.center, style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 16),
        Expanded(
          child: _ChoiceGrid(
            item: item,
            profile: profile,
            selectedId: selectedId,
            onChoose: onChoose,
          ),
        ),
      ],
    );
  }
}

class _ChoiceGrid extends StatelessWidget {
  const _ChoiceGrid({
    required this.item,
    required this.profile,
    required this.selectedId,
    required this.onChoose,
  });

  final ActivityItem item;
  final PlayerProfile profile;
  final String? selectedId;
  final Future<void> Function(ActivityChoice) onChoose;

  @override
  Widget build(BuildContext context) {
    final letterOrNumber =
        item.layout == PromptLayout.letterSelect || item.layout == PromptLayout.numberSelect;
    final cross = item.choices.length <= 2 ? 2 : (letterOrNumber ? 2 : 2);
    return GridView.count(
      crossAxisCount: cross,
      mainAxisSpacing: 12,
      crossAxisSpacing: 12,
      childAspectRatio: letterOrNumber ? 1.05 : 0.95,
      children: [
        for (final choice in item.choices)
          _ChoiceCard(
            choice: choice,
            selected: selectedId == choice.id,
            minHeight: profile.targetMin,
            largeText: profile.largeText,
            letterStyle: letterOrNumber,
            onTap: () => onChoose(choice),
          ),
      ],
    );
  }
}

class _ChoiceCard extends StatelessWidget {
  const _ChoiceCard({
    required this.choice,
    required this.selected,
    required this.minHeight,
    required this.largeText,
    required this.letterStyle,
    required this.onTap,
  });

  final ActivityChoice choice;
  final bool selected;
  final double minHeight;
  final bool largeText;
  final bool letterStyle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final high = Theme.of(context).brightness == Brightness.dark;
    final border = selected
        ? (high ? AppColors.highContrastAccent : AppColors.brand)
        : (high ? AppColors.highContrastAccent.withValues(alpha: 0.5) : AppColors.line);
    return Semantics(
      button: true,
      label: choice.imageAlt ?? choice.label,
      child: Material(
        color: high ? AppColors.highContrastSoft : AppColors.surface,
        borderRadius: BorderRadius.circular(24),
        child: InkWell(
          borderRadius: BorderRadius.circular(24),
          onTap: onTap,
          child: Ink(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: border, width: selected ? 4 : 2),
            ),
            child: ConstrainedBox(
              constraints: BoxConstraints(minHeight: minHeight),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      choice.emoji,
                      style: TextStyle(fontSize: letterStyle ? (largeText ? 56 : 44) : (largeText ? 48 : 40)),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      choice.label,
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontSize: letterStyle ? (largeText ? 36 : 28) : null,
                          ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _StoryThenObserve extends StatelessWidget {
  const _StoryThenObserve({
    required this.item,
    required this.profile,
    required this.storyDone,
    required this.storyIndex,
    required this.selectedId,
    required this.onPlayStory,
    required this.onFrame,
    required this.onStoryDone,
    required this.onChoose,
  });

  final ActivityItem item;
  final PlayerProfile profile;
  final bool storyDone;
  final int storyIndex;
  final String? selectedId;
  final VoidCallback onPlayStory;
  final void Function(int) onFrame;
  final VoidCallback onStoryDone;
  final Future<void> Function(ActivityChoice) onChoose;

  @override
  Widget build(BuildContext context) {
    if (!storyDone) {
      final frame = item.story[storyIndex];
      return Column(
        children: [
          Text('História em imagens', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Expanded(
            child: SectionCard(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(frame.emoji, style: TextStyle(fontSize: profile.largeText ? 96 : 80)),
                  const SizedBox(height: 12),
                  Text(frame.caption, textAlign: TextAlign.center, style: Theme.of(context).textTheme.headlineSmall),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          ListenButton(label: 'Ouvir história toda', large: true, onPressed: onPlayStory),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: storyIndex == 0 ? null : () => onFrame(storyIndex - 1),
                  child: const Text('Anterior'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: FilledButton(
                  onPressed: storyIndex < item.story.length - 1
                      ? () => onFrame(storyIndex + 1)
                      : onStoryDone,
                  child: Text(storyIndex < item.story.length - 1 ? 'Próxima imagem' : 'Recontar agora'),
                ),
              ),
            ],
          ),
        ],
      );
    }

    return Column(
      children: [
        Text('Registro da professora', style: Theme.of(context).textTheme.titleMedium?.copyWith(color: AppColors.muted)),
        const SizedBox(height: 6),
        Text(item.prompt, textAlign: TextAlign.center, style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 8),
        if (!profile.reducedStimulus)
          Wrap(
            spacing: 8,
            children: [
              for (final frame in item.story) Text(frame.emoji, style: const TextStyle(fontSize: 28)),
            ],
          ),
        const SizedBox(height: 12),
        Expanded(
          child: ListView(
            children: [
              for (final choice in item.choices) ...[
                SizedBox(
                  height: profile.targetMin + 8,
                  child: OutlinedButton(
                    style: OutlinedButton.styleFrom(
                      side: BorderSide(
                        color: selectedId == choice.id ? AppColors.brand : AppColors.line,
                        width: selectedId == choice.id ? 3 : 2,
                      ),
                      backgroundColor: selectedId == choice.id ? AppColors.brandSoft : AppColors.surface,
                    ),
                    onPressed: () => onChoose(choice),
                    child: Row(
                      children: [
                        Text(choice.emoji, style: const TextStyle(fontSize: 24)),
                        const SizedBox(width: 12),
                        Expanded(child: Text(choice.label, textAlign: TextAlign.left)),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 8),
              ],
            ],
          ),
        ),
      ],
    );
  }
}
