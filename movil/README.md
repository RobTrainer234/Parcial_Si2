# movil

## API base URL

La app usa una URL base centralizada en:

- `movil/lib/core/config/app_config.dart`

Por defecto apunta a:

- `http://localhost/api`

### Ejecutar contra Docker/Nginx

```bash
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost/api
```

### Ejecutar contra backend directo

```bash
flutter run -d chrome --dart-define=API_BASE_URL=http://127.0.0.1:8000/api
```
