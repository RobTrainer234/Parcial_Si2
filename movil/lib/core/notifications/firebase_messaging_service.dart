import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';

class FirebaseMessagingService {
  FirebaseMessagingService._();

  static final FirebaseMessagingService instance = FirebaseMessagingService._();

  FirebaseMessaging? _messaging;
  bool _initialized = false;

  Future<void> initialize() async {
    if (_initialized) return;
    try {
      await Firebase.initializeApp();
      _messaging = FirebaseMessaging.instance;
      _initialized = true;

      await _requestPermission();
      _configureHandlers();
    } catch (e) {
      debugPrint('FirebaseMessagingService: initialization skipped ($e)');
    }
  }

  Future<String?> getToken() async {
    if (_messaging == null) return null;
    try {
      return await _messaging!.getToken();
    } catch (e) {
      debugPrint('FirebaseMessagingService: getToken failed ($e)');
      return null;
    }
  }

  Future<void> _requestPermission() async {
    if (_messaging == null) return;
    try {
      final settings = await _messaging!.requestPermission(
        alert: true,
        badge: true,
        sound: true,
      );
      debugPrint(
        'FirebaseMessagingService: permission=${settings.authorizationStatus}',
      );
    } catch (e) {
      debugPrint('FirebaseMessagingService: permission error ($e)');
    }
  }

  void _configureHandlers() {
    if (_messaging == null) return;
    FirebaseMessaging.onMessage.listen(_handleForegroundMessage);
    FirebaseMessaging.onMessageOpenedApp.listen(_handleNotificationTap);
    FirebaseMessaging.onBackgroundMessage(_handleBackgroundMessage);
  }

  void _handleForegroundMessage(RemoteMessage message) {
    debugPrint(
      'FirebaseMessagingService: foreground message=${message.messageId}',
    );
  }

  void _handleNotificationTap(RemoteMessage message) {
    debugPrint(
      'FirebaseMessagingService: notification tapped=${message.messageId}',
    );
  }

  @pragma('vm:entry-point')
  static Future<void> _handleBackgroundMessage(RemoteMessage message) async {
    debugPrint(
      'FirebaseMessagingService: background message=${message.messageId}',
    );
  }
}
