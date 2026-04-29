import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/network/api_exception.dart';
import '../../../../core/routing/app_routes.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/app_page_scaffold.dart';
import '../../../../core/widgets/app_primary_button.dart';
import '../../data/repositories/auth_repository.dart';

class ClientRegisterVerifyPage extends ConsumerStatefulWidget {
  const ClientRegisterVerifyPage({
    super.key,
    required this.registrationToken,
    this.verificationCodeForTesting,
  });

  final String registrationToken;
  final String? verificationCodeForTesting;

  @override
  ConsumerState<ClientRegisterVerifyPage> createState() =>
      _ClientRegisterVerifyPageState();
}

class _ClientRegisterVerifyPageState
    extends ConsumerState<ClientRegisterVerifyPage> {
  final _formKey = GlobalKey<FormState>();
  final _codeController = TextEditingController();
  bool _isLoading = false;

  @override
  void dispose() {
    _codeController.dispose();
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

    setState(() => _isLoading = true);

    try {
      await ref.read(authRepositoryProvider).verifyClientRegistration(
            registrationToken: widget.registrationToken,
            verificationCode: _codeController.text.trim(),
          );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content:
                const Text('Registro completado. Ahora puedes iniciar sesión.'),
            backgroundColor: Theme.of(context).colorScheme.primary,
          ),
        );
        context.go(AppRoutes.login);
      }
    } catch (e) {
      if (e is ApiException) {
        String message;
        final detailStr = e.details?.toString().toLowerCase() ?? '';
        if (e.statusCode == 400) {
          if (detailStr.contains('invalid') || detailStr.contains('code')) {
            message = 'El código ingresado no es válido.';
          } else if (detailStr.contains('expir')) {
            message =
                'El código de verificación expiró. Inicia el registro nuevamente.';
          } else if (detailStr.contains('consumed') ||
              detailStr.contains('already')) {
            message = 'Este registro ya fue verificado.';
          } else {
            message = 'No se pudo verificar el registro.';
          }
        } else if (e.statusCode == 422) {
          message = 'Revisa el código ingresado.';
        } else if (e.statusCode == 409) {
          message = 'El registro entra en conflicto con datos existentes.';
        } else if (e.statusCode != null && e.statusCode! >= 500) {
          message =
              'No se pudo completar el registro por un problema del servidor.';
        } else {
          message =
              'No se pudo conectar con el servidor. Revisa tu conexión.';
        }
        _showError(message);
      } else {
        _showError(
            'No se pudo conectar con el servidor. Revisa tu conexión.');
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return AppPageScaffold(
      label: 'VERIFICACIÓN',
      title: 'Confirma tu registro',
      subtitle: 'Ingresa el código de verificación para crear tu cuenta.',
      child: Form(
        key: _formKey,
        child: ListView(
          children: [
            AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: theme.colorScheme.primary
                              .withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Icon(Icons.verified_user_outlined,
                            color: theme.colorScheme.primary),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Text(
                          'Verificación de cuenta',
                          style: theme.textTheme.titleLarge?.copyWith(
                            color: theme.colorScheme.primary,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Ingresa el código que recibiste para completar tu registro.',
                    style: theme.textTheme.bodyMedium,
                  ),
                  if (widget.verificationCodeForTesting != null) ...[
                    const SizedBox(height: 16),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: theme.colorScheme.surfaceContainerHighest,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        'Código de verificación para pruebas: ${widget.verificationCodeForTesting}',
                        style: theme.textTheme.bodyMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: theme.colorScheme.primary,
                        ),
                      ),
                    ),
                  ],
                  const SizedBox(height: 20),
                  TextFormField(
                    controller: _codeController,
                    decoration: const InputDecoration(
                      labelText: 'Código de verificación',
                      prefixIcon: Icon(Icons.pin_outlined),
                    ),
                    keyboardType: TextInputType.number,
                    enabled: !_isLoading,
                    validator: (v) {
                      if (v == null || v.trim().isEmpty) return 'Requerido';
                      if (v.trim().length < 4) return 'Mínimo 4 caracteres';
                      if (v.trim().length > 12) return 'Máximo 12 caracteres';
                      return null;
                    },
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            AppPrimaryButton(
              label: 'Verificar registro',
              isLoading: _isLoading,
              onPressed: _isLoading ? null : _submit,
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: _isLoading
                        ? null
                        : () => context.go(AppRoutes.registerClient),
                    child: const Text('Volver al registro'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: OutlinedButton(
                    onPressed: _isLoading
                        ? null
                        : () => context.go(AppRoutes.login),
                    child: const Text('Iniciar sesión'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}
