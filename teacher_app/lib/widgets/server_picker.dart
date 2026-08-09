import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../config/server_config.dart';
import '../state/app_state.dart';
import '../theme/app_colors.dart';

class ServerPicker extends StatelessWidget {
  const ServerPicker({super.key, this.compact = false});

  final bool compact;

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final target = state.settings.serverTarget;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (!compact) ...[
          Text('Servidor', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 4),
          Text(
            'Escolha o Django da web ou o que está rodando neste computador.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.muted),
          ),
          const SizedBox(height: 12),
        ] else ...[
          Text('Servidor', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 8),
        ],
        SegmentedButton<ServerTarget>(
          segments: const [
            ButtonSegment(
              value: ServerTarget.web,
              icon: Icon(Icons.cloud_outlined),
              label: Text('Web'),
            ),
            ButtonSegment(
              value: ServerTarget.local,
              icon: Icon(Icons.computer_outlined),
              label: Text('Local'),
            ),
          ],
          selected: {target},
          onSelectionChanged: (selected) => state.updateServer(target: selected.first),
        ),
        const SizedBox(height: 8),
        if (!compact)
          Text(
            ServerConfig.hint(target),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.muted),
          ),
        if (!compact) const SizedBox(height: 4),
        SelectableText(
          state.baseUrl,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(fontWeight: FontWeight.w600),
        ),
        if (!compact && target == ServerTarget.local) ...[
          const SizedBox(height: 12),
          const _LocalUrlField(),
        ],
      ],
    );
  }
}

class _LocalUrlField extends StatefulWidget {
  const _LocalUrlField();

  @override
  State<_LocalUrlField> createState() => _LocalUrlFieldState();
}

class _LocalUrlFieldState extends State<_LocalUrlField> {
  late final TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final url = context.read<AppState>().settings.localBaseUrl;
    if (_controller.text.isEmpty && url.isNotEmpty) {
      _controller.text = url;
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _save() {
    context.read<AppState>().updateServer(localBaseUrl: _controller.text);
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    if (_controller.text != state.settings.localBaseUrl && !FocusScope.of(context).hasFocus) {
      _controller.text = state.settings.localBaseUrl;
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        TextField(
          controller: _controller,
          keyboardType: TextInputType.url,
          textInputAction: TextInputAction.done,
          decoration: const InputDecoration(
            labelText: 'Endereço local',
            hintText: 'http://10.0.2.2:8000',
            helperText: 'Emulador: 10.0.2.2 · PC: 127.0.0.1 · tablet: IP do computador',
          ),
          onSubmitted: (_) => _save(),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          children: [
            FilledButton.tonal(
              onPressed: _save,
              child: const Text('Salvar endereço'),
            ),
            TextButton(
              onPressed: () {
                final url = ServerConfig.defaultLocalUrl();
                _controller.text = url;
                context.read<AppState>().updateServer(localBaseUrl: url);
              },
              child: const Text('Usar padrão'),
            ),
          ],
        ),
      ],
    );
  }
}
