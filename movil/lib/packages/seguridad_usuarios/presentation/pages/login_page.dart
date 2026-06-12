import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/auth/auth_controller.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/routing/app_routes.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/app_page_scaffold.dart';
import '../../../../core/widgets/app_primary_button.dart';
import '../../../../core/widgets/app_section_header.dart';

class LoginPage extends ConsumerStatefulWidget {
  const LoginPage({super.key, this.initialEmail, this.successMessage});

  final String? initialEmail;
  final String? successMessage;

  @override
  ConsumerState<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends ConsumerState<LoginPage> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _obscurePassword = true;

  @override
  void initState() {
    super.initState();
    final initialEmail = widget.initialEmail?.trim();
    if (initialEmail != null && initialEmail.isNotEmpty) {
      _emailController.text = initialEmail;
    }
    final successMessage = widget.successMessage?.trim();
    if (successMessage != null && successMessage.isNotEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(successMessage)));
      });
    }
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _showError(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Theme.of(context).colorScheme.error,
      ),
    );
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    try {
      debugPrint(
        'LoginPage: attempting login for ${_emailController.text.trim()}',
      );
      await ref
          .read(authControllerProvider.notifier)
          .login(_emailController.text.trim(), _passwordController.text);

      if (mounted) {
        final role = ref.read(authControllerProvider).valueOrNull?.role;
        debugPrint('LoginPage: login success role=$role');
        context.go(AppRoutes.homeForRole(role));
      }
    } catch (e) {
      debugPrint('LoginPage: login failed error=$e');
      if (e is ApiException) {
        String message = e.message;
        if (e.statusCode == 401) {
          message = 'Correo o contrasena incorrectos.';
        } else if (e.statusCode == 422) {
          message = 'Revisa los datos ingresados.';
        } else if (e.statusCode == 423) {
          final details = e.details as Map<String, dynamic>?;
          int? retryAfter;
          if (details != null) {
            if (details['retry_after_seconds'] != null) {
              retryAfter = details['retry_after_seconds'] as int?;
            } else if (details['detail'] is Map<String, dynamic> &&
                details['detail']['retry_after_seconds'] != null) {
              retryAfter = details['detail']['retry_after_seconds'] as int?;
            }
          }
          if (retryAfter != null) {
            message =
                'Cuenta bloqueada temporalmente. Intentalo nuevamente en $retryAfter segundos.';
          } else {
            message = 'Cuenta bloqueada temporalmente. Intentalo mas tarde.';
          }
        } else if (e.statusCode != null && e.statusCode! >= 500) {
          message = 'No se pudo iniciar sesion por un problema del servidor.';
        } else if (e.statusCode == null) {
          message = 'No se pudo conectar con el servidor. Revisa tu conexion.';
        }
        _showError(message);
      } else {
        _showError('No se pudo conectar con el servidor. Revisa tu conexion.');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authControllerProvider);
    final isLoading = authState.isLoading;
    final theme = Theme.of(context);

    return AppPageScaffold(
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: AppCard(
            padding: const EdgeInsets.all(24),
            child: Form(
              key: _formKey,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: theme.colorScheme.primary.withValues(
                            alpha: 0.12,
                          ),
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: Icon(
                          Icons.shield_outlined,
                          color: theme.colorScheme.primary,
                          size: 28,
                        ),
                      ),
                      const SizedBox(width: 16),
                      const Expanded(
                        child: AppSectionHeader(
                          label: 'ACCESO',
                          title: 'Auxilio Vial',
                          subtitle: 'Asistencia inteligente para conductores',
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  TextFormField(
                    controller: _emailController,
                    decoration: const InputDecoration(
                      labelText: 'Correo electronico',
                      prefixIcon: Icon(Icons.email_outlined),
                    ),
                    keyboardType: TextInputType.emailAddress,
                    enabled: !isLoading,
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return 'El correo es requerido';
                      }
                      if (!value.contains('@')) {
                        return 'Ingresa un correo valido';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _passwordController,
                    decoration: InputDecoration(
                      labelText: 'Contrasena',
                      prefixIcon: const Icon(Icons.lock_outline),
                      suffixIcon: IconButton(
                        onPressed: () {
                          setState(() {
                            _obscurePassword = !_obscurePassword;
                          });
                        },
                        icon: Icon(
                          _obscurePassword
                              ? Icons.visibility_outlined
                              : Icons.visibility_off_outlined,
                        ),
                      ),
                    ),
                    obscureText: _obscurePassword,
                    enabled: !isLoading,
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return 'La contrasena es requerida';
                      }
                      if (value.length < 8) {
                        return 'Debe tener al menos 8 caracteres';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 24),
                  AppPrimaryButton(
                    label: 'Iniciar sesion',
                    isLoading: isLoading,
                    onPressed: isLoading ? null : _submit,
                  ),
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton(
                      onPressed: isLoading
                          ? null
                          : () => context.push(AppRoutes.forgotPassword),
                      child: const Text('Olvide mi contrasena'),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Center(
                    child: TextButton(
                      onPressed: isLoading
                          ? null
                          : () => context.push(AppRoutes.registerClient),
                      child: Text(
                        'No tienes cuenta? Crear cuenta',
                        style: TextStyle(color: theme.colorScheme.primary),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
