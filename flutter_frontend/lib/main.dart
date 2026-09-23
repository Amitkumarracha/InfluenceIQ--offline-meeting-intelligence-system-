import 'package:flutter/material.dart';
import 'screens/login_screen.dart';
import 'screens/dashboard_screen.dart';

void main() {
  runApp(const MeetIQApp());
}

class MeetIQApp extends StatelessWidget {
  const MeetIQApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Meet IQ',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.indigo),
        useMaterial3: true,
        fontFamily: 'Inter',
      ),
      home: const LoginScreen(),
    );
  }
}
