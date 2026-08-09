import '../config/server_config.dart';

enum StudentStatus { pending, ok, attention }

enum ActivityMode { practice, survey }

enum PromptLayout {
  audioImage,
  numberSelect,
  storyThenObserve,
  tapGroup,
  letterSelect,
}

enum AccessibilityCode {
  visualScreenReader,
  visualHighContrast,
  visualLargeText,
  auditoryCaptions,
  auditoryVisualInstruction,
  auditoryLibras,
  motorLargeTarget,
  motorNoDrag,
  cognitiveShortInstructions,
  cognitiveExtraTime,
  cognitiveStepByStep,
  cognitiveNoTimeLimit,
  cognitiveRepeatInstructions,
  sensoryReducedMotion,
  sensoryReducedStimulus,
}

class AccessibilityFeature {
  const AccessibilityFeature({
    required this.code,
    required this.label,
    required this.category,
    required this.hint,
  });

  final AccessibilityCode code;
  final String label;
  final String category;
  final String hint;

  static const catalog = <AccessibilityFeature>[
    AccessibilityFeature(
      code: AccessibilityCode.visualLargeText,
      label: 'Texto ampliado',
      category: 'Visual',
      hint: 'Letras e imagens maiores.',
    ),
    AccessibilityFeature(
      code: AccessibilityCode.visualHighContrast,
      label: 'Alto contraste',
      category: 'Visual',
      hint: 'Fundo escuro e texto claro.',
    ),
    AccessibilityFeature(
      code: AccessibilityCode.visualScreenReader,
      label: 'Leitor de tela / áudio',
      category: 'Visual',
      hint: 'Lê em voz alta o enunciado e as opções.',
    ),
    AccessibilityFeature(
      code: AccessibilityCode.auditoryCaptions,
      label: 'Legendas',
      category: 'Auditiva',
      hint: 'Mostra o texto do áudio na tela.',
    ),
    AccessibilityFeature(
      code: AccessibilityCode.auditoryVisualInstruction,
      label: 'Instrução visual',
      category: 'Auditiva',
      hint: 'Ícones e imagens reforçam o que fazer.',
    ),
    AccessibilityFeature(
      code: AccessibilityCode.auditoryLibras,
      label: 'Libras',
      category: 'Auditiva',
      hint: 'Mostra dica visual em Libras.',
    ),
    AccessibilityFeature(
      code: AccessibilityCode.motorLargeTarget,
      label: 'Alvos ampliados',
      category: 'Motora',
      hint: 'Botões grandes, fáceis de tocar.',
    ),
    AccessibilityFeature(
      code: AccessibilityCode.motorNoDrag,
      label: 'Sem arrastar',
      category: 'Motora',
      hint: 'Tudo funciona com toque, sem arrastar.',
    ),
    AccessibilityFeature(
      code: AccessibilityCode.cognitiveShortInstructions,
      label: 'Instruções curtas',
      category: 'Atenção',
      hint: 'Frases curtas e objetivas.',
    ),
    AccessibilityFeature(
      code: AccessibilityCode.cognitiveStepByStep,
      label: 'Passo a passo',
      category: 'Atenção',
      hint: 'Mostra os passos antes de começar.',
    ),
    AccessibilityFeature(
      code: AccessibilityCode.cognitiveRepeatInstructions,
      label: 'Repetir instrução',
      category: 'Atenção',
      hint: 'Botão grande para ouvir de novo.',
    ),
    AccessibilityFeature(
      code: AccessibilityCode.cognitiveExtraTime,
      label: 'Tempo ampliado',
      category: 'Atenção',
      hint: 'Sem pressa. Sem cronômetro.',
    ),
    AccessibilityFeature(
      code: AccessibilityCode.cognitiveNoTimeLimit,
      label: 'Sem limite de tempo',
      category: 'Atenção',
      hint: 'A criança responde no próprio ritmo.',
    ),
    AccessibilityFeature(
      code: AccessibilityCode.sensoryReducedMotion,
      label: 'Menos movimento',
      category: 'Sensorial',
      hint: 'Sem animações de escala ou confete.',
    ),
    AccessibilityFeature(
      code: AccessibilityCode.sensoryReducedStimulus,
      label: 'Menos estímulos',
      category: 'Sensorial',
      hint: 'Tela mais simples, menos decoração.',
    ),
  ];

  static AccessibilityFeature byCode(AccessibilityCode code) {
    return catalog.firstWhere((f) => f.code == code);
  }
}

class TeacherUser {
  const TeacherUser({
    required this.username,
    required this.displayName,
    required this.schoolName,
    required this.classroomIds,
    this.id = '',
    this.role = 'PROFESSOR',
  });

  final String id;
  final String username;
  final String displayName;
  final String schoolName;
  final String role;
  final List<String> classroomIds;
}

class Student {
  const Student({
    required this.id,
    required this.fullName,
    required this.classroomId,
    required this.status,
    this.enrollmentId = '',
    this.features = const [],
    this.supportNotes = '',
  });

  final String id;
  final String enrollmentId;
  final String fullName;
  final String classroomId;
  final StudentStatus status;
  final List<AccessibilityCode> features;
  final String supportNotes;

  String get initials {
    final parts = fullName.trim().split(RegExp(r'\s+'));
    if (parts.length == 1) return parts.first.substring(0, 1).toUpperCase();
    return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
  }

  bool get hasSupport => features.isNotEmpty;

  bool has(AccessibilityCode code) => features.contains(code);
}

class Classroom {
  const Classroom({
    required this.id,
    required this.name,
    required this.grade,
    required this.schoolName,
    required this.students,
  });

  final String id;
  final String name;
  final String grade;
  final String schoolName;
  final List<Student> students;

  int get pendingCount => students.where((s) => s.status == StudentStatus.pending).length;
  int get okCount => students.where((s) => s.status == StudentStatus.ok).length;
  int get attentionCount => students.where((s) => s.status == StudentStatus.attention).length;
  int get supportCount => students.where((s) => s.hasSupport).length;
}

class ActivityChoice {
  const ActivityChoice({
    required this.id,
    required this.label,
    required this.emoji,
    this.audioText,
    this.imageAlt,
    this.isCorrect = false,
    this.scoreValue = 0,
  });

  final String id;
  final String label;
  final String emoji;
  final String? audioText;
  final String? imageAlt;
  final bool isCorrect;
  final int scoreValue;
}

class StoryFrame {
  const StoryFrame({
    required this.emoji,
    required this.caption,
    required this.audioText,
  });

  final String emoji;
  final String caption;
  final String audioText;
}

class ActivityItem {
  const ActivityItem({
    required this.id,
    required this.layout,
    required this.prompt,
    required this.promptShort,
    required this.audioText,
    required this.caption,
    required this.choices,
    this.emoji,
    this.imageAlt,
    this.steps = const [],
    this.librasHint,
    this.story = const [],
  });

  final String id;
  final PromptLayout layout;
  final String prompt;
  final String promptShort;
  final String audioText;
  final String caption;
  final String? emoji;
  final String? imageAlt;
  final List<String> steps;
  final String? librasHint;
  final List<ActivityChoice> choices;
  final List<StoryFrame> story;
}

class LudicActivity {
  const LudicActivity({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.emoji,
    required this.skillCode,
    required this.skillName,
    required this.dimension,
    required this.description,
    required this.estimatedMinutes,
    required this.accentToken,
    required this.resources,
    required this.items,
  });

  final String id;
  final String title;
  final String subtitle;
  final String emoji;
  final String skillCode;
  final String skillName;
  final String dimension;
  final String description;
  final int estimatedMinutes;
  final String accentToken;
  final List<String> resources;
  final List<ActivityItem> items;
}

class ItemAnswer {
  const ItemAnswer({
    required this.itemId,
    required this.choiceId,
    required this.correct,
    required this.score,
  });

  final String itemId;
  final String choiceId;
  final bool correct;
  final int score;
}

class ActivitySession {
  ActivitySession({
    required this.id,
    required this.student,
    required this.activity,
    required this.mode,
    required this.startedAt,
    this.answers = const [],
    this.completedAt,
    this.observation = '',
  });

  final String id;
  final Student student;
  final LudicActivity activity;
  final ActivityMode mode;
  final DateTime startedAt;
  List<ItemAnswer> answers;
  DateTime? completedAt;
  String observation;

  bool get isObservational =>
      activity.items.any((i) => i.layout == PromptLayout.storyThenObserve);

  int get totalScore => answers.fold(0, (sum, a) => sum + a.score);

  int get stars {
    if (answers.isEmpty) return 0;
    if (isObservational) {
      return switch (totalScore) { 3 => 5, 2 => 4, 1 => 2, _ => 1 };
    }
    final ratio = totalScore / answers.length;
    if (ratio >= 0.9) return 5;
    if (ratio >= 0.7) return 4;
    if (ratio >= 0.5) return 3;
    if (ratio >= 0.3) return 2;
    return 1;
  }

  String get pedagogicalLabel {
    if (isObservational) {
      return switch (totalScore) {
        3 => 'Habilidade demonstrada',
        2 => 'Desenvolvendo com apoio',
        1 => 'Necessita maior mediação',
        _ => 'Não observado',
      };
    }
    final ratio = totalScore / (answers.isEmpty ? 1 : answers.length);
    if (ratio >= 0.8) return 'Habilidade demonstrada';
    if (ratio >= 0.5) return 'Em desenvolvimento';
    return 'Necessita maior mediação';
  }

  bool get needsAttention {
    if (isObservational) return totalScore <= 1;
    final n = answers.isEmpty ? 1 : answers.length;
    return (totalScore / n) < 0.5;
  }
}

class AppSettings {
  AppSettings({
    this.forceLargeText = false,
    this.forceHighContrast = false,
    this.forceReducedMotion = false,
    this.ttsEnabled = true,
    this.serverTarget = ServerTarget.local,
    String? localBaseUrl,
  }) : localBaseUrl = localBaseUrl ?? ServerConfig.defaultLocalUrl();

  bool forceLargeText;
  bool forceHighContrast;
  bool forceReducedMotion;
  bool ttsEnabled;
  ServerTarget serverTarget;
  String localBaseUrl;

  String get baseUrl => serverTarget == ServerTarget.web
      ? ServerConfig.webUrl
      : ServerConfig.normalize(localBaseUrl.isEmpty ? ServerConfig.defaultLocalUrl() : localBaseUrl);
}
