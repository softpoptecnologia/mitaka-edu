import 'package:flutter/foundation.dart';

enum ServerTarget { web, local }

abstract final class ServerConfig {
  static const webUrl = 'https://edu.innomove.com.br';

  /// Emulador Android usa 10.0.2.2 para alcançar o PC. No tablet físico, use o IP da rede.
  static String defaultLocalUrl() {
    if (kIsWeb) return 'http://127.0.0.1:8000';
    if (defaultTargetPlatform == TargetPlatform.android) return 'http://10.0.2.2:8000';
    return 'http://127.0.0.1:8000';
  }

  static String normalize(String url) {
    var value = url.trim();
    if (value.endsWith('/')) value = value.substring(0, value.length - 1);
    return value;
  }

  static String label(ServerTarget target) => switch (target) {
        ServerTarget.web => 'Web',
        ServerTarget.local => 'Local',
      };

  static String hint(ServerTarget target) => switch (target) {
        ServerTarget.web => 'Servidor publicado (edu.innomove.com.br)',
        ServerTarget.local => 'Django neste computador (runserver)',
      };
}
