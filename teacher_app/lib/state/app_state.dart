import 'package:flutter/foundation.dart';

import '../data/activity_catalog.dart';
import '../data/demo_data.dart';
import '../models/models.dart';
import '../services/tts_service.dart';

class AppState extends ChangeNotifier {
  TeacherUser? user;
  List<Classroom> classrooms = const [];
  final sessions = <ActivitySession>[];
  final settings = AppSettings();
  final tts = TtsService();

  ActivitySession? activeSession;
  int activeIndex = 0;
  bool showSteps = true;

  bool get isLoggedIn => user != null;

  int get studentCount => classrooms.fold(0, (n, c) => n + c.students.length);
  int get pendingCount => classrooms.fold(0, (n, c) => n + c.pendingCount);
  int get okCount => classrooms.fold(0, (n, c) => n + c.okCount);
  int get attentionCount => classrooms.fold(0, (n, c) => n + c.attentionCount);

  List<Student> get attentionStudents => classrooms
      .expand((c) => c.students)
      .where((s) => s.status == StudentStatus.attention)
      .toList();

  bool login(String username, String password) {
    if (password != DemoData.password) return false;
    final found = DemoData.teachers.where(
      (t) => t.username.toLowerCase() == username.trim().toLowerCase(),
    );
    if (found.isEmpty) return false;
    user = found.first;
    classrooms = DemoData.classroomsFor(user!);
    notifyListeners();
    return true;
  }

  void logout() {
    user = null;
    classrooms = const [];
    activeSession = null;
    notifyListeners();
  }

  Classroom? classroomById(String id) {
    try {
      return classrooms.firstWhere((c) => c.id == id);
    } catch (_) {
      return null;
    }
  }

  Student? studentById(String id) {
    try {
      return classrooms.expand((c) => c.students).firstWhere((s) => s.id == id);
    } catch (_) {
      return null;
    }
  }

  LudicActivity activityById(String id) => ActivityCatalog.byId(id);

  PlayerProfile profileFor(Student student) {
    return PlayerProfile(
      largeText: settings.forceLargeText || student.has(AccessibilityCode.visualLargeText),
      highContrast: settings.forceHighContrast || student.has(AccessibilityCode.visualHighContrast),
      screenReader: student.has(AccessibilityCode.visualScreenReader),
      captions: student.has(AccessibilityCode.auditoryCaptions) ||
          student.has(AccessibilityCode.visualScreenReader),
      visualInstruction: student.has(AccessibilityCode.auditoryVisualInstruction),
      libras: student.has(AccessibilityCode.auditoryLibras),
      largeTarget: student.has(AccessibilityCode.motorLargeTarget),
      noDrag: true,
      shortInstructions: student.has(AccessibilityCode.cognitiveShortInstructions),
      stepByStep: student.has(AccessibilityCode.cognitiveStepByStep),
      repeatInstructions: student.has(AccessibilityCode.cognitiveRepeatInstructions) ||
          student.has(AccessibilityCode.visualScreenReader),
      reducedMotion: settings.forceReducedMotion ||
          student.has(AccessibilityCode.sensoryReducedMotion),
      reducedStimulus: student.has(AccessibilityCode.sensoryReducedStimulus),
      ttsEnabled: settings.ttsEnabled,
    );
  }

  void startSession({
    required Student student,
    required LudicActivity activity,
    required ActivityMode mode,
  }) {
    activeSession = ActivitySession(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      student: student,
      activity: activity,
      mode: mode,
      startedAt: DateTime.now(),
      answers: [],
    );
    activeIndex = 0;
    showSteps = profileFor(student).stepByStep;
    notifyListeners();
  }

  ActivityItem? get currentItem {
    final session = activeSession;
    if (session == null) return null;
    if (activeIndex >= session.activity.items.length) return null;
    return session.activity.items[activeIndex];
  }

  void dismissSteps() {
    showSteps = false;
    notifyListeners();
  }

  Future<void> speakCurrent() async {
    final item = currentItem;
    final session = activeSession;
    if (item == null || session == null) return;
    if (!profileFor(session.student).ttsEnabled) return;
    final profile = profileFor(session.student);
    final text = profile.shortInstructions ? item.promptShort : item.audioText;
    await tts.speak(text);
  }

  Future<void> speak(String text) async {
    if (!settings.ttsEnabled) return;
    await tts.speak(text);
  }

  void recordChoice(ActivityChoice choice) {
    final session = activeSession;
    final item = currentItem;
    if (session == null || item == null) return;
    final answer = ItemAnswer(
      itemId: item.id,
      choiceId: choice.id,
      correct: choice.isCorrect || choice.scoreValue > 0 && item.layout == PromptLayout.storyThenObserve,
      score: item.layout == PromptLayout.storyThenObserve
          ? choice.scoreValue
          : (choice.isCorrect ? 1 : 0),
    );
    session.answers = [...session.answers.where((a) => a.itemId != item.id), answer];
    notifyListeners();
  }

  bool nextItem() {
    final session = activeSession;
    if (session == null) return false;
    if (activeIndex < session.activity.items.length - 1) {
      activeIndex += 1;
      showSteps = profileFor(session.student).stepByStep;
      notifyListeners();
      return true;
    }
    return false;
  }

  void completeSession({String observation = ''}) {
    final session = activeSession;
    if (session == null) return;
    session.completedAt = DateTime.now();
    session.observation = observation;
    sessions.insert(0, session);
    activeSession = null;
    activeIndex = 0;
    notifyListeners();
  }

  void updateLastObservation(String observation) {
    if (sessions.isEmpty) return;
    sessions.first.observation = observation;
    notifyListeners();
  }

  void updateSetting({
    bool? largeText,
    bool? highContrast,
    bool? reducedMotion,
    bool? ttsEnabled,
  }) {
    if (largeText != null) settings.forceLargeText = largeText;
    if (highContrast != null) settings.forceHighContrast = highContrast;
    if (reducedMotion != null) settings.forceReducedMotion = reducedMotion;
    if (ttsEnabled != null) settings.ttsEnabled = ttsEnabled;
    notifyListeners();
  }
}

class PlayerProfile {
  const PlayerProfile({
    required this.largeText,
    required this.highContrast,
    required this.screenReader,
    required this.captions,
    required this.visualInstruction,
    required this.libras,
    required this.largeTarget,
    required this.noDrag,
    required this.shortInstructions,
    required this.stepByStep,
    required this.repeatInstructions,
    required this.reducedMotion,
    required this.reducedStimulus,
    required this.ttsEnabled,
  });

  final bool largeText;
  final bool highContrast;
  final bool screenReader;
  final bool captions;
  final bool visualInstruction;
  final bool libras;
  final bool largeTarget;
  final bool noDrag;
  final bool shortInstructions;
  final bool stepByStep;
  final bool repeatInstructions;
  final bool reducedMotion;
  final bool reducedStimulus;
  final bool ttsEnabled;

  double get textScale => largeText ? 1.28 : 1.0;
  double get targetMin => largeTarget ? 88 : 64;
}
