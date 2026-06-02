#!/usr/bin/env dart
/// Pure Dart (no Flutter, no web, no browser, no Dio) SSE streaming tester
/// for /chat/stream. Uses only dart:io + dart:convert.
/// This replicates the client's stream consumption path as closely as possible
/// without any of the mobile/web specific code.

import 'dart:convert';
import 'dart:io';

Future<void> main(List<String> args) async {
  final email = args.isNotEmpty ? args[0] : 'silvio-test-0602@osijek.ai';
  final password = args.length > 1 ? args[1] : 'TestLozinka123!';
  final message = args.length > 2 ? args[2] : 'Koje restorane preporučuješ u Osijeku?';

  print('=== Pure Dart Stream Tester ===');
  print('User: $email');
  print('Message: $message\n');

  // 1. Login
  final loginClient = HttpClient();
  try {
    final loginReq = await loginClient.postUrl(
        Uri.parse('https://osijek-ai-guide-production.up.railway.app/auth/login'));
    loginReq.headers.set('Content-Type', 'application/json');
    loginReq.write(jsonEncode({'email': email, 'password': password}));
    final loginResp = await loginReq.close();
    final loginBody = await loginResp.transform(utf8.decoder).join();
    final token = (jsonDecode(loginBody) as Map)['access_token'] as String?;
    if (token == null || token.isEmpty) {
      print('Login failed: $loginBody');
      return;
    }
    print('✓ Login OK, token len=${token.length}');

    // 2. Streaming request - exactly like the client (POST with query params)
    final uri = Uri.parse(
        'https://osijek-ai-guide-production.up.railway.app/chat/stream'
        '?message=${Uri.encodeComponent(message)}&language=hr&max_history=5');

    final client = HttpClient();
    final req = await client.postUrl(uri);
    req.headers.set('Authorization', 'Bearer $token');
    req.headers.set('Accept', 'text/event-stream');
    // Important: do not set responseType, just raw stream

    final resp = await req.close();
    print('✓ Response status: ${resp.statusCode}');
    print('  Content-Type: ${resp.headers.value('content-type')}');

    if (resp.statusCode >= 400) {
      final body = await resp.transform(utf8.decoder).join();
      print('Error body: $body');
      return;
    }

    // 3. Manual SSE parsing (similar to what the fixed chat_stream_service does)
    final buffer = StringBuffer();
    int chunkCount = 0;
    final contents = <String>[];

    await for (final data in resp) {
      chunkCount++;
      final chunk = utf8.decode(data);
      buffer.write(chunk);

      // Simple event extraction like the fixed client parser
      int idx;
      while ((idx = buffer.toString().indexOf('\n\n')) != -1) {
        final event = buffer.toString().substring(0, idx).trim();
        buffer.clear();
        buffer.write(buffer.toString().substring(idx + 2)); // keep tail

        if (event.isEmpty) continue;

        // Parse data: lines
        for (final line in event.split('\n')) {
          final trimmed = line.trim();
          if (trimmed.startsWith('data:')) {
            final dataPart = trimmed.substring(5).trim();
            if (dataPart == '[DONE]') {
              print('\n✓ Received [DONE]');
              continue;
            }
            try {
              final json = jsonDecode(dataPart);
              if (json is Map && json.containsKey('content')) {
                final c = json['content'] as String;
                contents.add(c);
                stdout.write(c); // live print like streaming
              } else if (json is Map && json.containsKey('error')) {
                print('\n✗ SSE error event: $json');
              }
            } catch (_) {
              if (dataPart.isNotEmpty && !dataPart.startsWith('{')) {
                contents.add(dataPart);
                stdout.write(dataPart);
              }
            }
          }
        }
      }
    }

    print('\n\n=== Summary ===');
    print('Chunks received: $chunkCount');
    print('Content chunks: ${contents.length}');
    print('Total content length: ${contents.join().length}');
    if (contents.isEmpty) {
      print('No content streamed (likely early error path returned JSON instead of SSE).');
    }
  } finally {
    loginClient.close(force: true);
  }
}
