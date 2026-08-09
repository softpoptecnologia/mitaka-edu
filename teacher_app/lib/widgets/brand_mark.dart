import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// Selo da marca Mitaka (logo sem fundo).
class BrandMark extends StatelessWidget {
  const BrandMark({
    super.key,
    this.size = 48,
    this.badge = true,
    this.fullLogo = false,
  });

  final double size;
  final bool badge;
  final bool fullLogo;

  @override
  Widget build(BuildContext context) {
    final high = Theme.of(context).brightness == Brightness.dark;
    final image = Image.asset(
      fullLogo ? 'assets/logo-sem-fundo.png' : 'assets/logo-mark.png',
      width: size,
      height: size,
      fit: BoxFit.contain,
      filterQuality: FilterQuality.medium,
    );
    final child = Semantics(
      label: 'Mitaka Edu',
      image: true,
      child: image,
    );
    if (!badge) return child;
    return Container(
      width: size + 12,
      height: size + 12,
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(
        color: high ? AppColors.highContrastSoft : Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: high ? Border.all(color: AppColors.highContrastAccent, width: 2) : null,
      ),
      child: child,
    );
  }
}

class MitakaHeader extends StatelessWidget {
  const MitakaHeader({super.key, this.title, this.subtitle});

  final String? title;
  final String? subtitle;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        const BrandMark(size: 36),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title ?? 'Mitaka Edu',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              if (subtitle != null)
                Text(
                  subtitle!,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.muted),
                ),
            ],
          ),
        ),
      ],
    );
  }
}
