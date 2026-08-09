import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import '../theme/app_colors.dart';
import '../widgets/brand_mark.dart';
import '../widgets/common.dart';
import '../widgets/server_picker.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _user = TextEditingController(text: 'professora');
  final _pass = TextEditingController(text: 'demo1234');
  String? _error;
  bool _obscure = true;
  bool _busy = false;

  @override
  void dispose() {
    _user.dispose();
    _pass.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    final error = await context.read<AppState>().login(_user.text, _pass.text);
    if (!mounted) return;
    setState(() {
      _busy = false;
      _error = error;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.cream,
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 440),
            child: ListView(
              padding: const EdgeInsets.all(24),
              children: [
                const SizedBox(height: 12),
                const Center(child: BrandMark(size: 72, fullLogo: true)),
                const SizedBox(height: 12),
                Text(
                  'Mitaka Edu',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
                const SizedBox(height: 8),
                Text(
                  'Evidências que transformam aprendizagens.',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(color: AppColors.muted),
                ),
                const SizedBox(height: 6),
                Text(
                  'Sondagem lúdica no tablet, sem arrastar e sem cronômetro.',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.muted),
                ),
                const SizedBox(height: 20),
                SectionCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text('Entrar', style: Theme.of(context).textTheme.titleLarge),
                      const SizedBox(height: 4),
                      Text(
                        'Acesso da professora. AEE, gestão e família usam o site.',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.muted),
                      ),
                      const SizedBox(height: 16),
                      const ServerPicker(compact: true),
                      const SizedBox(height: 16),
                      TextField(
                        controller: _user,
                        textInputAction: TextInputAction.next,
                        decoration: const InputDecoration(
                          labelText: 'Usuário',
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _pass,
                        obscureText: _obscure,
                        onSubmitted: (_) => _submit(),
                        decoration: InputDecoration(
                          labelText: 'Senha',
                          suffixIcon: IconButton(
                            tooltip: _obscure ? 'Mostrar senha' : 'Ocultar senha',
                            onPressed: () => setState(() => _obscure = !_obscure),
                            icon: Icon(_obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                          ),
                        ),
                      ),
                      if (_error != null) ...[
                        const SizedBox(height: 12),
                        Text(_error!, style: const TextStyle(color: Color(0xFFB42318), fontWeight: FontWeight.w700)),
                      ],
                      const SizedBox(height: 16),
                      FilledButton(
                        onPressed: _busy ? null : _submit,
                        child: Text(_busy ? 'Entrando…' : 'Entrar'),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  'Seed local: professora ou professor2\nSenha: demo1234',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.muted),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
