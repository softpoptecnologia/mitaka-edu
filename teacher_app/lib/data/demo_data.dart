import '../models/models.dart';

abstract final class DemoData {
  static const password = 'demo1234';

  static const teachers = <TeacherUser>[
    TeacherUser(
      username: 'professora',
      displayName: 'Ana Professora',
      schoolName: 'Creche Municipal Maria Inez de Melo',
      classroomIds: ['c1', 'c2', 'c3', 'c4'],
    ),
    TeacherUser(
      username: 'professor2',
      displayName: 'Bruno Professor',
      schoolName: 'Creche Municipal Noêmia Eloy de Melo (Tia Noêmia)',
      classroomIds: ['c5', 'c6'],
    ),
  ];

  static List<Classroom> classroomsFor(TeacherUser user) {
    return allClassrooms.where((c) => user.classroomIds.contains(c.id)).toList();
  }

  static final allClassrooms = <Classroom>[
    Classroom(
      id: 'c1',
      name: 'Infantil V A',
      grade: 'Infantil V',
      schoolName: 'Creche Municipal Maria Inez de Melo',
      students: const [
        Student(
          id: 's1',
          fullName: 'Luna Ferreira',
          classroomId: 'c1',
          status: StudentStatus.attention,
          features: [AccessibilityCode.visualLargeText, AccessibilityCode.visualHighContrast],
          supportNotes: 'Texto ampliado e alto contraste nas atividades.',
        ),
        Student(
          id: 's7',
          fullName: 'Laura Mendes',
          classroomId: 'c1',
          status: StudentStatus.ok,
          features: [
            AccessibilityCode.cognitiveShortInstructions,
            AccessibilityCode.cognitiveRepeatInstructions,
          ],
          supportNotes: 'Instruções curtas e repetição sempre visível.',
        ),
        Student(
          id: 's13',
          fullName: 'Isis Ribeiro',
          classroomId: 'c1',
          status: StudentStatus.pending,
        ),
        Student(
          id: 's19',
          fullName: 'Aurora Freitas',
          classroomId: 'c1',
          status: StudentStatus.ok,
        ),
        Student(
          id: 's25',
          fullName: 'Lizandra Pires',
          classroomId: 'c1',
          status: StudentStatus.pending,
        ),
      ],
    ),
    Classroom(
      id: 'c2',
      name: 'Infantil V B',
      grade: 'Infantil V',
      schoolName: 'Creche Municipal Maria Inez de Melo',
      students: const [
        Student(
          id: 's2',
          fullName: 'Theo Martins',
          classroomId: 'c2',
          status: StudentStatus.attention,
          features: [AccessibilityCode.visualScreenReader],
          supportNotes: 'Priorizar áudio e conteúdo legível por leitor de tela.',
        ),
        Student(
          id: 's8',
          fullName: 'Noah Barbosa',
          classroomId: 'c2',
          status: StudentStatus.ok,
          features: [
            AccessibilityCode.sensoryReducedMotion,
            AccessibilityCode.motorLargeTarget,
          ],
          supportNotes: 'Alvos amplos e sem animações.',
        ),
        Student(
          id: 's14',
          fullName: 'Samuel Pinto',
          classroomId: 'c2',
          status: StudentStatus.pending,
        ),
        Student(
          id: 's20',
          fullName: 'Miguel Correia',
          classroomId: 'c2',
          status: StudentStatus.ok,
        ),
        Student(
          id: 's26',
          fullName: 'Ravi Monteiro',
          classroomId: 'c2',
          status: StudentStatus.pending,
        ),
      ],
    ),
    Classroom(
      id: 'c3',
      name: 'Infantil IV A',
      grade: 'Infantil IV',
      schoolName: 'Escola Municipal Vereador Eliel Peixoto de Melo',
      students: const [
        Student(
          id: 's5',
          fullName: 'Helena Dias',
          classroomId: 'c3',
          status: StudentStatus.ok,
          features: [
            AccessibilityCode.auditoryCaptions,
            AccessibilityCode.auditoryVisualInstruction,
          ],
          supportNotes: 'Legendas e instrução visual quando houver áudio.',
        ),
        Student(
          id: 's11',
          fullName: 'Manuela Alves',
          classroomId: 'c3',
          status: StudentStatus.pending,
        ),
        Student(
          id: 's17',
          fullName: 'Liz Carvalho',
          classroomId: 'c3',
          status: StudentStatus.attention,
        ),
        Student(
          id: 's23',
          fullName: 'Eloá Moreira',
          classroomId: 'c3',
          status: StudentStatus.ok,
        ),
        Student(
          id: 's29',
          fullName: 'Ísis Fernandes',
          classroomId: 'c3',
          status: StudentStatus.pending,
        ),
      ],
    ),
    Classroom(
      id: 'c4',
      name: 'Infantil V A',
      grade: 'Infantil V',
      schoolName: 'Escola Municipal Ananias Crisóstomo',
      students: const [
        Student(
          id: 's6',
          fullName: 'Gael Oliveira',
          classroomId: 'c4',
          status: StudentStatus.attention,
          features: [
            AccessibilityCode.auditoryLibras,
            AccessibilityCode.auditoryVisualInstruction,
          ],
          supportNotes: 'Dica em Libras e apoio visual nas instruções.',
        ),
        Student(
          id: 's12',
          fullName: 'Davi Cardoso',
          classroomId: 'c4',
          status: StudentStatus.ok,
          features: [
            AccessibilityCode.motorNoDrag,
            AccessibilityCode.motorLargeTarget,
            AccessibilityCode.cognitiveStepByStep,
          ],
          supportNotes: 'Sem arrastar; alvos amplos; passos numerados.',
        ),
        Student(
          id: 's18',
          fullName: 'Heitor Ramos',
          classroomId: 'c4',
          status: StudentStatus.pending,
        ),
        Student(
          id: 's24',
          fullName: 'Joaquim Azevedo',
          classroomId: 'c4',
          status: StudentStatus.ok,
        ),
        Student(
          id: 's30',
          fullName: 'Enzo Batista',
          classroomId: 'c4',
          status: StudentStatus.pending,
        ),
      ],
    ),
    Classroom(
      id: 'c5',
      name: 'Infantil V A',
      grade: 'Infantil V',
      schoolName: 'Creche Municipal Noêmia Eloy de Melo (Tia Noêmia)',
      students: const [
        Student(
          id: 's3',
          fullName: 'Alice Rocha',
          classroomId: 'c5',
          status: StudentStatus.attention,
          features: [AccessibilityCode.motorNoDrag, AccessibilityCode.motorLargeTarget],
          supportNotes: 'Evitar arrastar; usar seleção e alvos amplos.',
        ),
        Student(
          id: 's9',
          fullName: 'Valentina Costa',
          classroomId: 'c5',
          status: StudentStatus.ok,
        ),
        Student(
          id: 's15',
          fullName: 'Cecília Nunes',
          classroomId: 'c5',
          status: StudentStatus.pending,
        ),
        Student(
          id: 's21',
          fullName: 'Maya Duarte',
          classroomId: 'c5',
          status: StudentStatus.ok,
        ),
        Student(
          id: 's27',
          fullName: 'Olívia Castro',
          classroomId: 'c5',
          status: StudentStatus.pending,
        ),
      ],
    ),
    Classroom(
      id: 'c6',
      name: '1º Ano A',
      grade: '1º Ano',
      schoolName: 'Escola Albino Moreira',
      students: const [
        Student(
          id: 's4',
          fullName: 'Benício Souza',
          classroomId: 'c6',
          status: StudentStatus.attention,
          features: [
            AccessibilityCode.sensoryReducedStimulus,
            AccessibilityCode.cognitiveStepByStep,
          ],
          supportNotes: 'Reduzir estímulos; instruções passo a passo.',
        ),
        Student(
          id: 's10',
          fullName: 'Arthur Lima',
          classroomId: 'c6',
          status: StudentStatus.ok,
        ),
        Student(
          id: 's16',
          fullName: 'Bernardo Teixeira',
          classroomId: 'c6',
          status: StudentStatus.pending,
        ),
        Student(
          id: 's22',
          fullName: 'Benjamin Lopes',
          classroomId: 'c6',
          status: StudentStatus.ok,
        ),
        Student(
          id: 's28',
          fullName: 'Caleb Moura',
          classroomId: 'c6',
          status: StudentStatus.pending,
        ),
      ],
    ),
  ];
}
