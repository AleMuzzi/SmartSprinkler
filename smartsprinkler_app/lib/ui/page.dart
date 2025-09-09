import 'package:flutter/material.dart';


abstract class PageWidget extends StatefulWidget {
  const PageWidget({super.key, required this.title});

  final String title;
}