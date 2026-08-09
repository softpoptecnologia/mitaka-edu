import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../config/server_config.dart';
import '../data/activity_catalog.dart';
import '../models/models.dart';
import '../services/teacher_api.dart';
import '../services/tts_service.dart';

class AppState extends ChangeNotifier {
  AppState({TeacherApi? api}) : api = api ?? HttpTeacherApi();

  final TeacherApi api;
  TeacherUser? user;
  List<Classroom> classrooms = const [];
  final sessions = <ActivitySession>[];
  final settings = AppSettings();
  final tts = TtsService();

  static const _kServerTarget = 'server_target';
  static const _kLocalBaseUrl = 'local_base_url';
  static const _kAuthToken = 'auth_token';

  bool loading = false;
  bool syncing = false;
  bool online = false;
  String? lastSyncError;

  String get baseUrl => settings.baseUrl;
  bool get isDemoApi => api is DemoTeacherApi;
  bool get isLoggedIn => user != null;

  ActivitySession? activeSession;
  int activeIndex = 0;
  bool showSteps = true;

  int get studentCount => classrooms.fold(0, (n, c) => n + c.students.length);
  int get pendingCount => classrooms.fold(0, (n, c) => n + c.pendingCount);
  int get okCount => classrooms.fold(0, (n, c) => n + c.okCount);
  int get attentionCount => classrooms.fold(0, (n, c) => n + c.attentionCount);

  List<Student> get pendingStudents => classrooms
      .expand((c) => c.students)
      .where((s) => s.status == StudentStatus.pending)
      .toList();

  List<Student> get attentionStudents => classrooms
      .expand((c) => c.students)
      .where((s) => s.status == StudentStatus.attention)
      .toList();

  List<Student> get okStudents => classrooms
      .expand((c) => c.students)
      .where((s) => s.status == StudentStatus.ok)
      .toList();

  List<Student> get todayQueue => [...pendingStudents, ...attentionStudents];

  Student? nextPendingAfter(String studentId) {
    final pending = pendingStudents;
    if (pending.isEmpty) return null;
    final index = pending.indexWhere((s) => s.id == studentId);
    if (index >= 0 && index + 1 < pending.length) {
      return pending[index + 1];
    }
    final others = pending.where((s) => s.id != studentId);
    return others.isEmpty ? null : others.first;
  }

  LudicActivity suggestedActivityFor(Student student) {
    final pool = switch (student.status) {
      StudentStatus.pending => const ['rimas', 'silabas', 'fonologica', 'letras'],
      StudentStatus.attention => const ['silabas', 'reconto', 'compreensao'],
      StudentStatus.ok => const ['vocabulario', 'letras', 'rimas'],
    };
    return ActivityCatalog.byId(pool[student.id.hashCode.abs() % pool.length]);
  }

  void abandonSession() {
    activeSession = null;
    activeIndex = 0;
    notifyListeners();
  }

  void _applyBootstrap(BootstrapData data) {
    user = data.teacher;
    classrooms = data.classrooms;
    online = !isDemoApi;
    lastSyncError = null;
  }

  Future<String?> login(String username, String password) async {
    loading = true;
    lastSyncError = null;
    notifyListeners();
    try {
      final data = await api.login(baseUrl, username, password);
      _applyBootstrap(data);
      await _savePrefs();
      return null;
    } on TeacherApiException catch (error) {
      lastSyncError = error.message;
      return error.message;
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<void> logout() async {
    final url = baseUrl;
    await api.logout(url);
    user = null;
    classrooms = const [];
    activeSession = null;
    online = false;
    await _savePrefs();
    notifyListeners();
  }

  Future<String?> refreshFromServer() async {
    if (!isLoggedIn) return 'Entre de novo para sincronizar.';
    syncing = true;
    notifyListeners();
    try {
      final data = await api.bootstrap(baseUrl);
      _applyBootstrap(data);
      await _savePrefs();
      return null;
    } on TeacherApiException catch (error) {
      lastSyncError = error.message;
      return error.message;
    } finally {
      syncing = false;
      notifyListeners();
    }
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
    if (!isDemoApi) syncing = true;
    notifyListeners();
    syncLudic(session);
  }

  Future<String?> updateLastObservation(String observation) async {
    if (sessions.isEmpty) return null;
    sessions.first.observation = observation;
    notifyListeners();
    return syncLudic(sessions.first);
  }

  Future<String?> syncLudic(ActivitySession session) async {
    if (isDemoApi) return null;
    syncing = true;
    lastSyncError = null;
    notifyListeners();
    try {
      final data = await api.submitLudic(
        baseUrl,
        LudicSyncPayload(
          studentId: session.student.id,
          enrollmentId: session.student.enrollmentId,
          activityId: session.activity.id,
          activityTitle: session.activity.title,
          skillCode: session.activity.skillCode,
          mode: session.mode == ActivityMode.survey ? 'survey' : 'practice',
          label: session.pedagogicalLabel,
          score: session.totalScore,
          total: session.answers.isEmpty ? 1 : session.answers.length,
          needsAttention: session.needsAttention,
          observational: session.isObservational,
          observation: session.observation,
          answers: session.answers,
        ),
      );
      _applyBootstrap(data);
      return null;
    } on TeacherApiException catch (error) {
      lastSyncError = error.message;
      return error.message;
    } finally {
      syncing = false;
      notifyListeners();
    }
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

  Future<void> loadPrefs() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final target = prefs.getString(_kServerTarget);
      if (target == ServerTarget.web.name) {
        settings.serverTarget = ServerTarget.web;
      } else if (target == ServerTarget.local.name) {
        settings.serverTarget = ServerTarget.local;
      }
      final localUrl = prefs.getString(_kLocalBaseUrl);
      if (localUrl != null && localUrl.trim().isNotEmpty) {
        settings.localBaseUrl = ServerConfig.normalize(localUrl);
      }
      final savedToken = prefs.getString(_kAuthToken);
      if (savedToken != null && savedToken.isNotEmpty && !isDemoApi) {
        api.token = savedToken;
        try {
          final data = await api.bootstrap(baseUrl);
          _applyBootstrap(data);
        } catch (_) {
          api.token = null;
        }
      }
      notifyListeners();
    } catch (_) {}
  }

  void updateServer({ServerTarget? target, String? localBaseUrl}) {
    final changedTarget = target != null && target != settings.serverTarget;
    if (target != null) settings.serverTarget = target;
    if (localBaseUrl != null) {
      settings.localBaseUrl = ServerConfig.normalize(localBaseUrl);
    }
    if (settings.localBaseUrl.isEmpty) {
      settings.localBaseUrl = ServerConfig.defaultLocalUrl();
    }
    if (changedTarget && isLoggedIn && !isDemoApi) {
      user = null;
      classrooms = const [];
      api.token = null;
      online = false;
    }
    notifyListeners();
    _savePrefs();
  }

  Future<void> _savePrefs() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_kServerTarget, settings.serverTarget.name);
      await prefs.setString(_kLocalBaseUrl, settings.localBaseUrl);
      if (api.token != null && api.token!.isNotEmpty) {
        await prefs.setString(_kAuthToken, api.token!);
      } else {
        await prefs.remove(_kAuthToken);
      }
    } catch (_) {}
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
