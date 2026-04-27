import 'package:flutter/material.dart';

import 'app_section_header.dart';

class AppPageScaffold extends StatelessWidget {
  const AppPageScaffold({
    super.key,
    required this.child,
    this.label,
    this.title,
    this.subtitle,
    this.actions,
    this.padding = const EdgeInsets.fromLTRB(20, 12, 20, 24),
  });

  final Widget child;
  final String? label;
  final String? title;
  final String? subtitle;
  final Widget? actions;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    final hasHeader = label != null || title != null || subtitle != null;

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: padding,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (hasHeader) ...[
                AppSectionHeader(
                  label: label ?? '',
                  title: title ?? '',
                  subtitle: subtitle,
                  action: actions,
                ),
                const SizedBox(height: 24),
              ],
              Expanded(child: child),
            ],
          ),
        ),
      ),
    );
  }
}
