import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/network/api_exception.dart';
import '../../../../core/routing/app_routes.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/app_page_scaffold.dart';
import '../../../../core/widgets/app_primary_button.dart';
import '../../data/models/client_register_start_request_model.dart';
import '../../data/models/vehicle_registration_model.dart';
import '../../data/repositories/auth_repository.dart';

class ClientRegisterPage extends ConsumerStatefulWidget {
  const ClientRegisterPage({super.key});

  @override
  ConsumerState<ClientRegisterPage> createState() => _ClientRegisterPageState();
}

class _ClientRegisterPageState extends ConsumerState<ClientRegisterPage> {
  final _formKey = GlobalKey<FormState>();
  bool _isLoading = false;
  bool _obscurePassword = true;
  bool _obscureConfirm = true;

  // Personal
  final _nombreController = TextEditingController();
  final _apellidoController = TextEditingController();
  final _ciController = TextEditingController();
  final _telefonoController = TextEditingController();
  final _direccionController = TextEditingController();

  // Access
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();

  // Vehicle
  final _placaController = TextEditingController();
  final _anioController = TextEditingController();
  final _marcaController = TextEditingController();
  final _modeloController = TextEditingController();
  final _colorController = TextEditingController();

  @override
  void dispose() {
    _nombreController.dispose();
    _apellidoController.dispose();
    _ciController.dispose();
    _telefonoController.dispose();
    _direccionController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    _placaController.dispose();
    _anioController.dispose();
    _marcaController.dispose();
    _modeloController.dispose();
    _colorController.dispose();
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

  String _mapConflictMessage(dynamic details) {
    final detailStr = details?.toString().toLowerCase() ?? '';
    if (detailStr.contains('email')) {
      return 'Ese correo ya está registrado.';
    }
    if (detailStr.contains('ci')) {
      return 'Ese CI ya está registrado.';
    }
    if (detailStr.contains('phone') || detailStr.contains('telefono')) {
      return 'Ese teléfono ya está registrado.';
    }
    if (detailStr.contains('plate') || detailStr.contains('placa')) {
      return 'Esa placa ya está registrada.';
    }
    return 'Ya existe un registro con esos datos.';
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    try {
      final direccion = _direccionController.text.trim();
      final request = ClientRegisterStartRequestModel(
        nombre: _nombreController.text.trim(),
        apellido: _apellidoController.text.trim(),
        ci: _ciController.text.trim(),
        telefono: _telefonoController.text.trim(),
        direccion: direccion.isEmpty ? null : direccion,
        email: _emailController.text.trim(),
        password: _passwordController.text,
        vehicles: [
          VehicleRegistrationModel(
            placa: _placaController.text.trim().toUpperCase(),
            anio: int.parse(_anioController.text.trim()),
            marcaNombre: _marcaController.text.trim(),
            modeloNombre: _modeloController.text.trim(),
            colorNombre: _colorController.text.trim(),
          ),
        ],
      );

      final response = await ref
          .read(authRepositoryProvider)
          .startClientRegistration(request);

      if (mounted) {
        context.push(
          AppRoutes.registerClientVerify,
          extra: {
            'registration_token': response.registrationToken,
            'verification_code_for_testing':
                response.verificationCodeForTesting,
          },
        );
      }
    } catch (e) {
      if (e is ApiException) {
        String message;
        if (e.statusCode == 409) {
          message = _mapConflictMessage(e.details);
        } else if (e.statusCode == 422) {
          message = 'Revisa los datos ingresados.';
        } else if (e.statusCode == 400) {
          message =
              'No se pudo iniciar el registro. Revisa los datos enviados.';
        } else if (e.statusCode != null && e.statusCode! >= 500) {
          message =
              'No se pudo iniciar el registro por un problema del servidor.';
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
      label: 'REGISTRO',
      title: 'Crear cuenta',
      subtitle: 'Registra tus datos para solicitar auxilio vial.',
      child: Form(
        key: _formKey,
        child: ListView(
          children: [
            // --- Datos personales ---
            _SectionTitle(title: 'Datos personales'),
            const SizedBox(height: 12),
            AppCard(
              child: Column(
                children: [
                  TextFormField(
                    controller: _nombreController,
                    decoration: const InputDecoration(
                      labelText: 'Nombre',
                      prefixIcon: Icon(Icons.person_outline),
                    ),
                    textCapitalization: TextCapitalization.words,
                    enabled: !_isLoading,
                    validator: (v) =>
                        (v == null || v.trim().isEmpty) ? 'Requerido' : null,
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _apellidoController,
                    decoration: const InputDecoration(
                      labelText: 'Apellido',
                      prefixIcon: Icon(Icons.person_outline),
                    ),
                    textCapitalization: TextCapitalization.words,
                    enabled: !_isLoading,
                    validator: (v) =>
                        (v == null || v.trim().isEmpty) ? 'Requerido' : null,
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _ciController,
                    decoration: const InputDecoration(
                      labelText: 'CI',
                      prefixIcon: Icon(Icons.badge_outlined),
                    ),
                    enabled: !_isLoading,
                    validator: (v) =>
                        (v == null || v.trim().isEmpty) ? 'Requerido' : null,
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _telefonoController,
                    decoration: const InputDecoration(
                      labelText: 'Teléfono',
                      prefixIcon: Icon(Icons.phone_outlined),
                    ),
                    keyboardType: TextInputType.phone,
                    enabled: !_isLoading,
                    validator: (v) =>
                        (v == null || v.trim().isEmpty) ? 'Requerido' : null,
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _direccionController,
                    decoration: const InputDecoration(
                      labelText: 'Dirección (opcional)',
                      prefixIcon: Icon(Icons.location_on_outlined),
                    ),
                    enabled: !_isLoading,
                  ),
                ],
              ),
            ),

            const SizedBox(height: 24),

            // --- Datos de acceso ---
            _SectionTitle(title: 'Datos de acceso'),
            const SizedBox(height: 12),
            AppCard(
              child: Column(
                children: [
                  TextFormField(
                    controller: _emailController,
                    decoration: const InputDecoration(
                      labelText: 'Correo electrónico',
                      prefixIcon: Icon(Icons.email_outlined),
                    ),
                    keyboardType: TextInputType.emailAddress,
                    enabled: !_isLoading,
                    validator: (v) {
                      if (v == null || v.trim().isEmpty) return 'Requerido';
                      if (!v.contains('@')) return 'Correo no válido';
                      return null;
                    },
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _passwordController,
                    decoration: InputDecoration(
                      labelText: 'Contraseña',
                      prefixIcon: const Icon(Icons.lock_outline),
                      suffixIcon: IconButton(
                        onPressed: () =>
                            setState(() => _obscurePassword = !_obscurePassword),
                        icon: Icon(_obscurePassword
                            ? Icons.visibility_outlined
                            : Icons.visibility_off_outlined),
                      ),
                    ),
                    obscureText: _obscurePassword,
                    enabled: !_isLoading,
                    validator: (v) {
                      if (v == null || v.isEmpty) return 'Requerido';
                      if (v.length < 8) return 'Mínimo 8 caracteres';
                      return null;
                    },
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _confirmPasswordController,
                    decoration: InputDecoration(
                      labelText: 'Confirmar contraseña',
                      prefixIcon: const Icon(Icons.lock_outline),
                      suffixIcon: IconButton(
                        onPressed: () =>
                            setState(() => _obscureConfirm = !_obscureConfirm),
                        icon: Icon(_obscureConfirm
                            ? Icons.visibility_outlined
                            : Icons.visibility_off_outlined),
                      ),
                    ),
                    obscureText: _obscureConfirm,
                    enabled: !_isLoading,
                    validator: (v) {
                      if (v == null || v.isEmpty) return 'Requerido';
                      if (v != _passwordController.text) {
                        return 'Las contraseñas no coinciden';
                      }
                      return null;
                    },
                  ),
                ],
              ),
            ),

            const SizedBox(height: 24),

            // --- Vehículo ---
            _SectionTitle(title: 'Vehículo inicial'),
            const SizedBox(height: 12),
            AppCard(
              child: Column(
                children: [
                  TextFormField(
                    controller: _placaController,
                    decoration: const InputDecoration(
                      labelText: 'Placa',
                      prefixIcon: Icon(Icons.directions_car_outlined),
                    ),
                    textCapitalization: TextCapitalization.characters,
                    enabled: !_isLoading,
                    validator: (v) {
                      if (v == null || v.trim().isEmpty) return 'Requerido';
                      if (v.trim().length < 3) return 'Mínimo 3 caracteres';
                      if (v.trim().length > 15) return 'Máximo 15 caracteres';
                      return null;
                    },
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _anioController,
                    decoration: const InputDecoration(
                      labelText: 'Año',
                      prefixIcon: Icon(Icons.calendar_today_outlined),
                    ),
                    keyboardType: TextInputType.number,
                    enabled: !_isLoading,
                    validator: (v) {
                      if (v == null || v.trim().isEmpty) return 'Requerido';
                      final year = int.tryParse(v.trim());
                      if (year == null) return 'Año no válido';
                      if (year < 1900 || year > 2100) {
                        return 'Entre 1900 y 2100';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _marcaController,
                    decoration: const InputDecoration(
                      labelText: 'Marca',
                      prefixIcon: Icon(Icons.branding_watermark_outlined),
                    ),
                    textCapitalization: TextCapitalization.words,
                    enabled: !_isLoading,
                    validator: (v) =>
                        (v == null || v.trim().isEmpty) ? 'Requerido' : null,
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _modeloController,
                    decoration: const InputDecoration(
                      labelText: 'Modelo',
                      prefixIcon: Icon(Icons.time_to_leave_outlined),
                    ),
                    textCapitalization: TextCapitalization.words,
                    enabled: !_isLoading,
                    validator: (v) =>
                        (v == null || v.trim().isEmpty) ? 'Requerido' : null,
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _colorController,
                    decoration: const InputDecoration(
                      labelText: 'Color',
                      prefixIcon: Icon(Icons.color_lens_outlined),
                    ),
                    textCapitalization: TextCapitalization.words,
                    enabled: !_isLoading,
                    validator: (v) =>
                        (v == null || v.trim().isEmpty) ? 'Requerido' : null,
                  ),
                ],
              ),
            ),

            const SizedBox(height: 24),

            AppPrimaryButton(
              label: 'Continuar',
              isLoading: _isLoading,
              onPressed: _isLoading ? null : _submit,
            ),

            const SizedBox(height: 16),

            Center(
              child: TextButton(
                onPressed:
                    _isLoading ? null : () => context.go(AppRoutes.login),
                child: Text(
                  '¿Ya tienes cuenta? Inicia sesión',
                  style: TextStyle(color: theme.colorScheme.primary),
                ),
              ),
            ),

            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.title});
  final String title;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Text(
      title,
      style: theme.textTheme.titleMedium?.copyWith(
        color: theme.colorScheme.onSurfaceVariant,
      ),
    );
  }
}
