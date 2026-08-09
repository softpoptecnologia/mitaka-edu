import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import '../theme/app_colors.dart';
import '../widgets/common.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    return SafeArea(
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
        children: [
          Text('Ajustes', style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 4),
          Text(
            'Estes ajustes do tablet se somam ao perfil do estudante. Sem degradês e sem cronômetro.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.muted),
          ),
          const SizedBox(height: 16),
          SectionCard(
            padding: EdgeInsets.zero,
            child: Column(
              children: [
                SwitchListTile(
                  title: const Text('Texto ampliado'),
                  subtitle: const Text('Letras maiores em todo o app'),
                  value: state.settings.forceLargeText,
                  onChanged: (v) => state.updateSetting(largeText: v),
                ),
                SwitchListTile(
                  title: const Text('Alto contraste'),
                  subtitle: const Text('Fundo escuro, texto claro — sem degradê'),
                  value: state.settings.forceHighContrast,
                  onChanged: (v) => state.updateSetting(highContrast: v),
                ),
                SwitchListTile(
                  title: const Text('Menos movimento'),
                  subtitle: const Text('Sem animações de escala'),
                  value: state.settings.forceReducedMotion,
                  onChanged: (v) => state.updateSetting(reducedMotion: v),
                ),
                SwitchListTile(
                  title: const Text('Áudio (voz)'),
                  subtitle: const Text('Ler enunciados e opções em voz alta'),
                  value: state.settings.ttsEnabled,
                  onChanged: (v) => state.updateSetting(ttsEnabled: v),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          SectionCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(state.user?.displayName ?? '', style: Theme.of(context).textTheme.titleLarge),
                Text(state.user?.schoolName ?? '', style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.muted)),
                const SizedBox(height: 12),
                OutlinedButton.icon(
                  onPressed: () => state.logout(),
                  icon: const Icon(Icons.logout_rounded),
                  label: const Text('Sair'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
