import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Lead form: name + phone + preferred time. The patient's photo + AI result are
/// attached server-side via generation_id (the core B2B value — clinic sees the
/// desired smile before calling).
class LeadFormScreen extends StatefulWidget {
  const LeadFormScreen({super.key, required this.clinicId});

  final String clinicId;

  @override
  State<LeadFormScreen> createState() => _LeadFormScreenState();
}

class _LeadFormScreenState extends State<LeadFormScreen> {
  final _name = TextEditingController();
  final _phone = TextEditingController();
  String? _time;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Book a consultation')),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            TextField(
              controller: _name,
              decoration: const InputDecoration(labelText: 'Name'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _phone,
              keyboardType: TextInputType.phone,
              decoration: const InputDecoration(labelText: 'Phone'),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              value: _time,
              decoration: const InputDecoration(labelText: 'Preferred time'),
              items: const [
                DropdownMenuItem(value: 'morning', child: Text('Morning')),
                DropdownMenuItem(value: 'afternoon', child: Text('Afternoon')),
                DropdownMenuItem(value: 'evening', child: Text('Evening')),
              ],
              onChanged: (v) => setState(() => _time = v),
            ),
            const Spacer(),
            FilledButton(
              // TODO(phase-5): ApiClient.submitLead(clinicId, generationId, ...).
              onPressed: () => context.go('/lead/sent'),
              child: const Text('Send request'),
            ),
          ],
        ),
      ),
    );
  }
}
