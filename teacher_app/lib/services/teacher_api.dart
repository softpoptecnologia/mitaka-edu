import 'dart:convert';

import 'package:http/http.dart' as http;

import '../data/demo_data.dart';
import '../models/models.dart';

class TeacherApiException implements Exception {
  TeacherApiException(this.message);
  final String message;

  @override
  String toString() => message;
}

class BootstrapData {
  const BootstrapData({required this.teacher, required this.classrooms});
  final TeacherUser teacher;
  final List<Classroom> classrooms;
}

class LudicSyncPayload {
  const LudicSyncPayload({
    required this.studentId,
    required this.activityId,
    required this.activityTitle,
    required this.skillCode,
    required this.mode,
    required this.label,
    required this.score,
    required this.total,
    required this.needsAttention,
    required this.observational,
    this.enrollmentId = '',
    this.observation = '',
    this.answers = const [],
  });

  final String studentId;
  final String enrollmentId;
  final String activityId;
  final String activityTitle;
  final String skillCode;
  final String mode;
  final String label;
  final int score;
  final int total;
  final bool needsAttention;
  final bool observational;
  final String observation;
  final List<ItemAnswer> answers;

  Map<String, dynamic> toJson() => {
        'student_id': int.tryParse(studentId) ?? studentId,
        if (enrollmentId.isNotEmpty) 'enrollment_id': int.tryParse(enrollmentId) ?? enrollmentId,
        'activity_id': activityId,
        'activity_title': activityTitle,
        'skill_code': skillCode,
        'mode': mode,
        'label': label,
        'score': score,
        'total': total,
        'needs_attention': needsAttention,
        'observational': observational,
        'observation': observation,
        'answers': [
          for (final a in answers) {'item_id': a.itemId, 'choice_id': a.choiceId, 'correct': a.correct, 'score': a.score},
        ],
      };
}

abstract class TeacherApi {
  String? token;

  Future<BootstrapData> login(String baseUrl, String username, String password);
  Future<void> logout(String baseUrl);
  Future<BootstrapData> bootstrap(String baseUrl);
  Future<BootstrapData> submitLudic(String baseUrl, LudicSyncPayload payload);
}

class HttpTeacherApi implements TeacherApi {
  HttpTeacherApi({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;
  @override
  String? token;

  Uri _uri(String baseUrl, String path) {
    final root = baseUrl.endsWith('/') ? baseUrl.substring(0, baseUrl.length - 1) : baseUrl;
    return Uri.parse('$root$path');
  }

  Map<String, String> _headers({bool auth = true}) => {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        if (auth && token != null && token!.isNotEmpty) 'Authorization': 'Token $token',
      };

  Future<Map<String, dynamic>> _read(http.Response response, {String fallback = 'Não foi possível falar com o servidor.'}) async {
    Map<String, dynamic> body = {};
    if (response.body.isNotEmpty) {
      try {
        final decoded = jsonDecode(response.body);
        if (decoded is Map<String, dynamic>) body = decoded;
      } catch (_) {}
    }
    if (response.statusCode >= 200 && response.statusCode < 300) return body;
    final detail = (body['detail'] ?? body['error'] ?? '').toString().trim();
    if (response.statusCode == 401 || response.statusCode == 403) {
      throw TeacherApiException(detail.isEmpty ? 'Acesso não autorizado.' : detail);
    }
    if (response.statusCode == 404) {
      throw TeacherApiException(
        'Este servidor ainda não tem o login do app. No Local rode migrate; na Web publique o código novo.',
      );
    }
    if (response.statusCode >= 500) {
      throw TeacherApiException(
        detail.isEmpty ? 'O servidor falhou no login. No Local rode: python manage.py migrate.' : detail,
      );
    }
    throw TeacherApiException(detail.isEmpty ? fallback : detail);
  }

  Future<Map<String, dynamic>> _send(Future<http.Response> Function() request, {String fallback = 'Não foi possível falar com o servidor.'}) async {
    try {
      final response = await request().timeout(const Duration(seconds: 15));
      return _read(response, fallback: fallback);
    } on TeacherApiException {
      rethrow;
    } catch (_) {
      throw TeacherApiException('Não conectou ao servidor. Confira Web/Local e se o Django está no ar.');
    }
  }

  BootstrapData _parseBootstrap(Map<String, dynamic> json) {
    final teacherJson = (json['teacher'] as Map?)?.cast<String, dynamic>() ?? {};
    final rooms = <Classroom>[];
    for (final raw in (json['classrooms'] as List? ?? const [])) {
      if (raw is! Map) continue;
      rooms.add(_parseClassroom(raw.cast<String, dynamic>()));
    }
    return BootstrapData(
      teacher: TeacherUser(
        id: '${teacherJson['id'] ?? ''}',
        username: '${teacherJson['username'] ?? ''}',
        displayName: '${teacherJson['display_name'] ?? teacherJson['username'] ?? 'Professora'}',
        schoolName: '${teacherJson['school_name'] ?? ''}',
        role: '${teacherJson['role'] ?? 'PROFESSOR'}',
        classroomIds: [
          for (final id in (teacherJson['classroom_ids'] as List? ?? rooms.map((r) => r.id))) '$id',
        ],
      ),
      classrooms: rooms,
    );
  }

  Classroom _parseClassroom(Map<String, dynamic> json) {
    final id = '${json['id']}';
    return Classroom(
      id: id,
      name: '${json['name'] ?? ''}',
      grade: '${json['grade'] ?? ''}',
      schoolName: '${json['school_name'] ?? ''}',
      students: [
        for (final raw in (json['students'] as List? ?? const []))
          if (raw is Map) _parseStudent(raw.cast<String, dynamic>(), id),
      ],
    );
  }

  Student _parseStudent(Map<String, dynamic> json, String classroomId) {
    final statusRaw = '${json['status'] ?? 'pending'}';
    final status = switch (statusRaw) {
      'attention' => StudentStatus.attention,
      'ok' => StudentStatus.ok,
      _ => StudentStatus.pending,
    };
    final codes = <AccessibilityCode>[];
    for (final code in (json['feature_codes'] as List? ?? const [])) {
      final mapped = accessibilityFromApi('$code');
      if (mapped != null) codes.add(mapped);
    }
    return Student(
      id: '${json['id']}',
      enrollmentId: '${json['enrollment_id'] ?? ''}',
      fullName: '${json['full_name'] ?? ''}',
      classroomId: classroomId,
      status: status,
      features: codes,
      supportNotes: '${json['support_notes'] ?? ''}',
    );
  }

  @override
  Future<BootstrapData> login(String baseUrl, String username, String password) async {
    final body = await _send(
      () => _client.post(
        _uri(baseUrl, '/api/auth/login/'),
        headers: _headers(auth: false),
        body: jsonEncode({'username': username, 'password': password}),
      ),
      fallback: 'Não foi possível entrar. Confira usuário, senha e o servidor.',
    );
    token = '${body['token'] ?? ''}';
    if (token == null || token!.isEmpty) {
      throw TeacherApiException('O servidor não devolveu o token de acesso.');
    }
    return _parseBootstrap(body);
  }

  @override
  Future<void> logout(String baseUrl) async {
    try {
      await _send(() => _client.post(_uri(baseUrl, '/api/auth/logout/'), headers: _headers()));
    } catch (_) {
      // Local logout still happens even if the server is offline.
    } finally {
      token = null;
    }
  }

  @override
  Future<BootstrapData> bootstrap(String baseUrl) async {
    final body = await _send(
      () => _client.get(_uri(baseUrl, '/api/professor/bootstrap/'), headers: _headers()),
      fallback: 'Não foi possível carregar as turmas do servidor.',
    );
    return _parseBootstrap(body);
  }

  @override
  Future<BootstrapData> submitLudic(String baseUrl, LudicSyncPayload payload) async {
    final body = await _send(
      () => _client.post(
        _uri(baseUrl, '/api/professor/atividades-ludicas/'),
        headers: _headers(),
        body: jsonEncode(payload.toJson()),
      ),
      fallback: 'A atividade não foi gravada no servidor.',
    );
    final bootstrap = body['bootstrap'];
    if (bootstrap is Map<String, dynamic>) return _parseBootstrap(bootstrap);
    return this.bootstrap(baseUrl);
  }
}

class DemoTeacherApi implements TeacherApi {
  @override
  String? token = 'demo-token';

  @override
  Future<BootstrapData> login(String baseUrl, String username, String password) async {
    if (password != DemoData.password) {
      throw TeacherApiException('Usuário ou senha inválidos.');
    }
    final found = DemoData.teachers.where((t) => t.username.toLowerCase() == username.trim().toLowerCase());
    if (found.isEmpty) {
      const webOnly = {'aee', 'familia', 'gestor', 'coordenador', 'secretaria', 'tecnico', 'admin'};
      if (webOnly.contains(username.trim().toLowerCase())) {
        throw TeacherApiException('Este app é só para a professora. AEE, gestão e família usam a web.');
      }
      throw TeacherApiException('Usuário ou senha inválidos.');
    }
    final teacher = found.first;
    return BootstrapData(teacher: teacher, classrooms: DemoData.classroomsFor(teacher));
  }

  @override
  Future<void> logout(String baseUrl) async {
    token = null;
  }

  @override
  Future<BootstrapData> bootstrap(String baseUrl) async {
    final teacher = DemoData.teachers.first;
    return BootstrapData(teacher: teacher, classrooms: DemoData.classroomsFor(teacher));
  }

  @override
  Future<BootstrapData> submitLudic(String baseUrl, LudicSyncPayload payload) => bootstrap(baseUrl);
}

AccessibilityCode? accessibilityFromApi(String code) {
  const map = {
    'VISUAL_SCREEN_READER': AccessibilityCode.visualScreenReader,
    'VISUAL_HIGH_CONTRAST': AccessibilityCode.visualHighContrast,
    'VISUAL_LARGE_TEXT': AccessibilityCode.visualLargeText,
    'AUDITORY_CAPTIONS': AccessibilityCode.auditoryCaptions,
    'AUDITORY_VISUAL_INSTRUCTION': AccessibilityCode.auditoryVisualInstruction,
    'AUDITORY_LIBRAS': AccessibilityCode.auditoryLibras,
    'MOTOR_LARGE_TARGET': AccessibilityCode.motorLargeTarget,
    'MOTOR_NO_DRAG': AccessibilityCode.motorNoDrag,
    'COGNITIVE_SHORT_INSTRUCTIONS': AccessibilityCode.cognitiveShortInstructions,
    'COGNITIVE_EXTRA_TIME': AccessibilityCode.cognitiveExtraTime,
    'COGNITIVE_STEP_BY_STEP': AccessibilityCode.cognitiveStepByStep,
    'COGNITIVE_NO_TIME_LIMIT': AccessibilityCode.cognitiveNoTimeLimit,
    'COGNITIVE_REPEAT_INSTRUCTIONS': AccessibilityCode.cognitiveRepeatInstructions,
    'SENSORY_REDUCED_MOTION': AccessibilityCode.sensoryReducedMotion,
    'SENSORY_REDUCED_STIMULUS': AccessibilityCode.sensoryReducedStimulus,
  };
  return map[code];
}
