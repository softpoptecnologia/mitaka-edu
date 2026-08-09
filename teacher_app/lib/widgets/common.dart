import 'package:flutter/material.dart';

import '../models/models.dart';
import '../theme/app_colors.dart';

Color accentSolid(String token) {
  switch (token) {
    case 'coral':
      return AppColors.coral;
    case 'sky':
      return AppColors.sky;
    case 'grape':
      return AppColors.grape;
    case 'ok':
      return AppColors.ok;
    case 'sun':
      return AppColors.sun;
    case 'attention':
      return AppColors.attention;
    default:
      return AppColors.brand;
  }
}

Color accentSoft(String token) {
  switch (token) {
    case 'coral':
      return AppColors.coralSoft;
    case 'sky':
      return AppColors.skySoft;
    case 'grape':
      return AppColors.grapeSoft;
    case 'ok':
      return AppColors.okSoft;
    case 'sun':
      return AppColors.sunSoft;
    case 'attention':
      return AppColors.attentionSoft;
    default:
      return AppColors.brandSoft;
  }
}

class StatusChip extends StatelessWidget {
  const StatusChip({super.key, required this.status});

  final StudentStatus status;

  @override
  Widget build(BuildContext context) {
    final (label, color, bg) = switch (status) {
      StudentStatus.ok => ('Regular', AppColors.ok, AppColors.okSoft),
      StudentStatus.attention => ('Atenção', AppColors.attention, AppColors.attentionSoft),
      StudentStatus.pending => ('Pendente', AppColors.pending, AppColors.pendingSoft),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontWeight: FontWeight.w800, fontSize: 12),
      ),
    );
  }
}

class ResourceChip extends StatelessWidget {
  const ResourceChip({super.key, required this.label, this.compact = false});

  final String label;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final high = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: EdgeInsets.symmetric(horizontal: compact ? 8 : 10, vertical: compact ? 4 : 6),
      decoration: BoxDecoration(
        color: high ? AppColors.highContrastSoft : AppColors.brandSoft,
        borderRadius: BorderRadius.circular(999),
        border: high ? Border.all(color: AppColors.highContrastAccent) : null,
      ),
      child: Text(
        label,
        style: TextStyle(
          color: high ? AppColors.highContrastAccent : AppColors.brandDark,
          fontWeight: FontWeight.w700,
          fontSize: compact ? 11 : 12,
        ),
      ),
    );
  }
}

class StudentAvatar extends StatelessWidget {
  const StudentAvatar({super.key, required this.student, this.size = 48});

  final Student student;
  final double size;

  @override
  Widget build(BuildContext context) {
    final high = Theme.of(context).brightness == Brightness.dark;
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: high ? AppColors.highContrastAccent : AppColors.brandSoft,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Text(
        student.initials,
        style: TextStyle(
          color: high ? Colors.black : AppColors.brandDark,
          fontWeight: FontWeight.w800,
          fontSize: size * 0.32,
        ),
      ),
    );
  }
}

class StatCard extends StatelessWidget {
  const StatCard({
    super.key,
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
    required this.soft,
  });

  final String label;
  final String value;
  final IconData icon;
  final Color color;
  final Color soft;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Theme.of(context).cardTheme.color ?? AppColors.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Theme.of(context).dividerColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(color: soft, borderRadius: BorderRadius.circular(12)),
            child: Icon(icon, color: color, size: 20),
          ),
          const SizedBox(height: 12),
          Text(value, style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 2),
          Text(label, style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.muted)),
        ],
      ),
    );
  }
}

class SectionCard extends StatelessWidget {
  const SectionCard({super.key, required this.child, this.padding});

  final Widget child;
  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: padding ?? const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).cardTheme.color ?? AppColors.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Theme.of(context).dividerColor),
      ),
      child: child,
    );
  }
}

class StarRow extends StatelessWidget {
  const StarRow({super.key, required this.count, this.size = 28});

  final int count;
  final double size;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        for (var i = 1; i <= 5; i++)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 2),
            child: Icon(
              i <= count ? Icons.star_rounded : Icons.star_outline_rounded,
              color: i <= count ? AppColors.sun : AppColors.muted,
              size: size,
            ),
          ),
      ],
    );
  }
}

class ProgressDots extends StatelessWidget {
  const ProgressDots({super.key, required this.total, required this.current});

  final int total;
  final int current;

  @override
  Widget build(BuildContext context) {
    final high = Theme.of(context).brightness == Brightness.dark;
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        for (var i = 0; i < total; i++)
          Container(
            width: i == current ? 22 : 10,
            height: 10,
            margin: const EdgeInsets.symmetric(horizontal: 3),
            decoration: BoxDecoration(
              color: i <= current
                  ? (high ? AppColors.highContrastAccent : AppColors.brand)
                  : (high ? AppColors.highContrastSoft : AppColors.line),
              borderRadius: BorderRadius.circular(999),
            ),
          ),
      ],
    );
  }
}

class ListenButton extends StatelessWidget {
  const ListenButton({
    super.key,
    required this.onPressed,
    this.label = 'Ouvir',
    this.large = false,
  });

  final VoidCallback onPressed;
  final String label;
  final bool large;

  @override
  Widget build(BuildContext context) {
    final high = Theme.of(context).brightness == Brightness.dark;
    return FilledButton.icon(
      onPressed: onPressed,
      icon: const Icon(Icons.volume_up_rounded),
      label: Text(label),
      style: FilledButton.styleFrom(
        minimumSize: Size(large ? 200 : 48, large ? 64 : 48),
        backgroundColor: high ? AppColors.highContrastAccent : AppColors.sky,
        foregroundColor: high ? Colors.black : Colors.white,
      ),
    );
  }
}

class CaptionBar extends StatelessWidget {
  const CaptionBar({super.key, required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    final high = Theme.of(context).brightness == Brightness.dark;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: high ? AppColors.highContrastSoft : AppColors.skySoft,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: high ? AppColors.highContrastAccent : AppColors.sky),
      ),
      child: Text(
        text,
        textAlign: TextAlign.center,
        style: Theme.of(context).textTheme.titleMedium,
      ),
    );
  }
}
