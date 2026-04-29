import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final themeModeControllerProvider =
    StateNotifierProvider<ThemeModeController, ThemeMode>(
  (ref) => ThemeModeController(),
);

class ThemeModeController extends StateNotifier<ThemeMode> {
  ThemeModeController() : super(ThemeMode.system);

  void toggle(Brightness platformBrightness) {
    final isDarkActive = state == ThemeMode.dark ||
        (state == ThemeMode.system && platformBrightness == Brightness.dark);

    state = isDarkActive ? ThemeMode.light : ThemeMode.dark;
  }
}
