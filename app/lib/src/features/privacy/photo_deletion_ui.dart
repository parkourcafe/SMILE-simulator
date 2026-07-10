import 'package:flutter/material.dart';

import '../../api/models.dart';

Future<bool> confirmPhotoDeletion(BuildContext context) async {
  return await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Удалить фото?'),
          content: const Text(
            'Исходное фото, визуализация и техническая маска будут удалены из хранилища. Это действие нельзя отменить.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Отмена'),
            ),
            TextButton.icon(
              style: TextButton.styleFrom(
                foregroundColor: Theme.of(context).colorScheme.error,
              ),
              onPressed: () => Navigator.pop(context, true),
              icon: const Icon(Icons.delete_outline),
              label: const Text('Удалить'),
            ),
          ],
        ),
      ) ??
      false;
}

String photoDeletionMessage(PhotoDeletionReceipt receipt) => receipt.isPending
    ? 'Фото скрыты. Удаление из хранилища будет повторено автоматически.'
    : 'Фото удалены.';
