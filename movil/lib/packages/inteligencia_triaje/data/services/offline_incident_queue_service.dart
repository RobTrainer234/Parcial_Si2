import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';

import '../../../../core/network/api_exception.dart';
import '../models/offline_incident_queue_item.dart';
import '../repositories/triage_repository.dart';

final offlineIncidentQueueServiceProvider =
    Provider<OfflineIncidentQueueService>((ref) {
      final repository = ref.watch(triageRepositoryProvider);
      return OfflineIncidentQueueService(repository);
    });

class OfflineIncidentQueueService {
  static const _storageKey = 'offline_incident_queue_v1';
  static const _offlineMediaWarningPrefix =
      'Advertencia de persistencia offline:';

  final TriageRepository _repository;
  final FlutterSecureStorage _storage;

  OfflineIncidentQueueService(this._repository)
    : _storage = const FlutterSecureStorage(
        aOptions: AndroidOptions(encryptedSharedPreferences: true),
      );

  Future<List<OfflineIncidentQueueItem>> getQueue({
    int? clientPersonaId,
  }) async {
    final allItems = await _readAll();
    final filtered = clientPersonaId == null
        ? allItems
        : allItems
              .where((item) => item.clientPersonaId == clientPersonaId)
              .toList();
    filtered.sort((a, b) => b.createdAtLocal.compareTo(a.createdAtLocal));
    return filtered;
  }

  Future<OfflineIncidentQueueItem> enqueue({
    required int clientPersonaId,
    required String localUuid,
    required int vehicleId,
    required String description,
    required int specialtyId,
    required String specialtyLabel,
    required double latitud,
    required double longitud,
    required List<String> photoPaths,
    required String? audioPath,
  }) async {
    final items = await _readAll();
    items.removeWhere(
      (item) =>
          item.clientPersonaId == clientPersonaId &&
          item.localUuid == localUuid,
    );
    final persistedMedia = await _persistOfflineMedia(
      localUuid: localUuid,
      photoPaths: photoPaths,
      audioPath: audioPath,
    );
    final queuedItem = OfflineIncidentQueueItem(
      localUuid: localUuid,
      clientPersonaId: clientPersonaId,
      vehicleId: vehicleId,
      description: description,
      specialtyId: specialtyId,
      specialtyLabel: specialtyLabel,
      latitud: latitud,
      longitud: longitud,
      photoPaths: persistedMedia.photoPaths,
      audioPath: persistedMedia.audioPath,
      status: OfflineIncidentSyncStatus.pendienteSync,
      createdAtLocal: DateTime.now(),
      lastError: persistedMedia.warning,
      serverIncidentId: null,
    );
    items.add(queuedItem);
    await _writeAll(items);
    return queuedItem;
  }

  Future<List<OfflineIncidentQueueItem>> syncPending({
    int? clientPersonaId,
  }) async {
    final items = await _readAll();
    for (var index = 0; index < items.length; index++) {
      final item = items[index];
      if (clientPersonaId != null && item.clientPersonaId != clientPersonaId) {
        continue;
      }
      if (item.status == OfflineIncidentSyncStatus.sincronizado) {
        continue;
      }

      items[index] = item.copyWith(
        status: OfflineIncidentSyncStatus.sincronizando,
      );
      await _writeAll(items);

      final syncWarnings = <String>[];
      final persistedMediaWarning = _extractPersistentMediaWarning(
        item.lastError,
      );
      if (persistedMediaWarning != null) {
        syncWarnings.add(persistedMediaWarning);
      }
      final availableImages = <XFile>[];
      for (final path in item.photoPaths) {
        if (File(path).existsSync()) {
          availableImages.add(XFile(path));
        } else {
          syncWarnings.add(
            'No se encontro una foto adjunta durante la sincronizacion.',
          );
        }
      }

      String? availableAudioPath;
      final audioPath = item.audioPath;
      if (audioPath != null && audioPath.trim().isNotEmpty) {
        if (File(audioPath).existsSync()) {
          availableAudioPath = audioPath;
        } else {
          syncWarnings.add(
            'No se encontro el audio adjunto durante la sincronizacion.',
          );
        }
      }

      try {
        final response = await _repository.reportIncident(
          vehicleId: item.vehicleId,
          latitud: item.latitud,
          longitud: item.longitud,
          descripcionCliente: item.description,
          specialtyId: item.specialtyId,
          localUuid: item.localUuid,
          offlineSync: true,
          images: availableImages,
          audioPath: availableAudioPath,
        );
        items[index] = item.copyWith(
          status: OfflineIncidentSyncStatus.sincronizado,
          serverIncidentId: response.incidentId,
          lastError: syncWarnings.isEmpty ? null : syncWarnings.join(' '),
          clearLastError: syncWarnings.isEmpty,
        );
        await _writeAll(items);
      } on ApiException catch (error) {
        final syncError = _buildSyncErrorMessage(error, syncWarnings);
        items[index] = item.copyWith(
          status: OfflineIncidentSyncStatus.errorSync,
          lastError: syncError,
          clearServerIncidentId: true,
        );
        await _writeAll(items);
      } catch (_) {
        final syncError = [
          if (syncWarnings.isNotEmpty) syncWarnings.join(' '),
          'No se pudo sincronizar la emergencia.',
        ].join(' ').trim();
        items[index] = item.copyWith(
          status: OfflineIncidentSyncStatus.errorSync,
          lastError: syncError,
          clearServerIncidentId: true,
        );
        await _writeAll(items);
      }
    }
    return getQueue(clientPersonaId: clientPersonaId);
  }

  String generateLocalUuid() {
    final random = Random.secure();
    String segment(int length) => List.generate(
      length,
      (_) => random.nextInt(16).toRadixString(16),
    ).join();
    return '${segment(8)}-${segment(4)}-${segment(4)}-${segment(4)}-${segment(12)}';
  }

  String _buildSyncErrorMessage(ApiException error, List<String> warnings) {
    final segments = <String>[if (warnings.isNotEmpty) warnings.join(' ')];
    if (error.statusCode == 400 || error.statusCode == 422) {
      segments.add(
        'El reporte sincronizado ya no es valido. Revisa descripcion y archivos.',
      );
    } else if (error.statusCode == 401 || error.statusCode == 403) {
      segments.add('Tu sesion expiro antes de sincronizar la emergencia.');
    } else if (error.statusCode == 404) {
      segments.add(
        'El vehiculo asociado ya no esta disponible para sincronizar.',
      );
    } else if (error.statusCode != null && error.statusCode! >= 500) {
      segments.add('El servidor rechazo temporalmente la sincronizacion.');
    } else {
      segments.add(error.message);
    }
    return segments.join(' ').trim();
  }

  Future<_PersistedOfflineMedia> _persistOfflineMedia({
    required String localUuid,
    required List<String> photoPaths,
    required String? audioPath,
  }) async {
    final warnings = <String>[];
    Directory? targetDirectory;

    try {
      final supportDirectory = await getApplicationSupportDirectory();
      targetDirectory = Directory(
        '${supportDirectory.path}${Platform.pathSeparator}offline_incidents${Platform.pathSeparator}$localUuid',
      );
      await targetDirectory.create(recursive: true);
    } catch (error) {
      warnings.add(
        'No se pudo preparar el directorio persistente offline. Se conservan rutas originales.',
      );
      return _PersistedOfflineMedia(
        photoPaths: photoPaths,
        audioPath: audioPath,
        warning: _buildPersistenceWarning(warnings),
      );
    }

    final persistedPhotos = <String>[];
    for (var index = 0; index < photoPaths.length; index++) {
      final originalPath = photoPaths[index];
      persistedPhotos.add(
        await _copyToPersistentLocation(
          sourcePath: originalPath,
          destinationPath:
              '${targetDirectory.path}${Platform.pathSeparator}photo_${index + 1}${_normalizedExtension(originalPath, fallback: '.jpg')}',
          onErrorMessage:
              'No se pudo copiar una foto al almacenamiento offline persistente.',
          warnings: warnings,
        ),
      );
    }

    String? persistedAudioPath;
    if (audioPath != null && audioPath.trim().isNotEmpty) {
      persistedAudioPath = await _copyToPersistentLocation(
        sourcePath: audioPath,
        destinationPath:
            '${targetDirectory.path}${Platform.pathSeparator}audio${_normalizedExtension(audioPath, fallback: '.m4a')}',
        onErrorMessage:
            'No se pudo copiar el audio al almacenamiento offline persistente.',
        warnings: warnings,
      );
    }

    return _PersistedOfflineMedia(
      photoPaths: persistedPhotos,
      audioPath: persistedAudioPath,
      warning: _buildPersistenceWarning(warnings),
    );
  }

  Future<String> _copyToPersistentLocation({
    required String sourcePath,
    required String destinationPath,
    required String onErrorMessage,
    required List<String> warnings,
  }) async {
    final normalizedSource = sourcePath.trim();
    if (normalizedSource.isEmpty) {
      warnings.add(onErrorMessage);
      return sourcePath;
    }

    try {
      final sourceFile = File(normalizedSource);
      if (!await sourceFile.exists()) {
        warnings.add('$onErrorMessage No se encontro el archivo original.');
        return sourcePath;
      }

      final normalizedDestination = destinationPath.trim();
      if (_pathsEqual(normalizedSource, normalizedDestination)) {
        return normalizedSource;
      }

      final copiedFile = await sourceFile.copy(normalizedDestination);
      return copiedFile.path;
    } catch (_) {
      warnings.add(onErrorMessage);
      return sourcePath;
    }
  }

  String? _buildPersistenceWarning(List<String> warnings) {
    if (warnings.isEmpty) {
      return null;
    }
    return '$_offlineMediaWarningPrefix ${warnings.join(' ')}';
  }

  String? _extractPersistentMediaWarning(String? lastError) {
    final normalized = lastError?.trim();
    if (normalized == null || normalized.isEmpty) {
      return null;
    }
    if (!normalized.startsWith(_offlineMediaWarningPrefix)) {
      return null;
    }
    return normalized;
  }

  String _normalizedExtension(String path, {required String fallback}) {
    final extension = _fileExtension(path).toLowerCase();
    return extension.isEmpty ? fallback : extension;
  }

  String _fileExtension(String path) {
    final normalized = path.replaceAll('\\', '/');
    final fileName = normalized.split('/').last;
    final dotIndex = fileName.lastIndexOf('.');
    if (dotIndex <= 0 || dotIndex == fileName.length - 1) {
      return '';
    }
    return fileName.substring(dotIndex);
  }

  bool _pathsEqual(String left, String right) {
    final normalizedLeft = left.replaceAll('\\', '/').trim();
    final normalizedRight = right.replaceAll('\\', '/').trim();
    return normalizedLeft == normalizedRight;
  }

  Future<List<OfflineIncidentQueueItem>> _readAll() async {
    final raw = await _storage.read(key: _storageKey);
    if (raw == null || raw.trim().isEmpty) {
      return [];
    }
    try {
      final decoded = jsonDecode(raw);
      if (decoded is! List<dynamic>) {
        return [];
      }
      return decoded
          .whereType<Map>()
          .map((item) => Map<String, dynamic>.from(item))
          .map(OfflineIncidentQueueItem.fromJson)
          .toList();
    } catch (_) {
      return [];
    }
  }

  Future<void> _writeAll(List<OfflineIncidentQueueItem> items) async {
    final encoded = jsonEncode(items.map((item) => item.toJson()).toList());
    await _storage.write(key: _storageKey, value: encoded);
  }
}

class _PersistedOfflineMedia {
  final List<String> photoPaths;
  final String? audioPath;
  final String? warning;

  const _PersistedOfflineMedia({
    required this.photoPaths,
    required this.audioPath,
    required this.warning,
  });
}
