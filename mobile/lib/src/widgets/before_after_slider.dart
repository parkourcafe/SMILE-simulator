import 'package:flutter/material.dart';

/// Draggable before/after comparison (CLAUDE.md: "most engaging result format").
///
/// [before] is revealed on the left of the divider, [after] fills the rest.
/// Drag the handle (or tap) to move the divider.
class BeforeAfterSlider extends StatefulWidget {
  const BeforeAfterSlider({
    super.key,
    required this.before,
    required this.after,
    this.initial = 0.5,
  });

  final Widget before;
  final Widget after;
  final double initial;

  @override
  State<BeforeAfterSlider> createState() => _BeforeAfterSliderState();
}

class _BeforeAfterSliderState extends State<BeforeAfterSlider> {
  late double _pos = widget.initial.clamp(0.0, 1.0);

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final w = constraints.maxWidth;
        void update(double dx) =>
            setState(() => _pos = (dx / w).clamp(0.0, 1.0));

        return GestureDetector(
          onTapDown: (d) => update(d.localPosition.dx),
          onHorizontalDragUpdate: (d) => update(d.localPosition.dx),
          child: Stack(
            children: [
              Positioned.fill(child: widget.after),
              Positioned.fill(
                child: ClipRect(
                  clipper: _LeftClipper(_pos),
                  child: widget.before,
                ),
              ),
              Positioned(
                left: _pos * w - 1,
                top: 0,
                bottom: 0,
                child: Container(width: 2, color: Colors.white),
              ),
              Positioned(
                left: _pos * w - 18,
                top: 0,
                bottom: 0,
                child: Center(
                  child: Container(
                    width: 36,
                    height: 36,
                    decoration: const BoxDecoration(
                      color: Colors.white,
                      shape: BoxShape.circle,
                      boxShadow: [BoxShadow(blurRadius: 4, color: Colors.black26)],
                    ),
                    child: const Icon(Icons.compare_arrows, size: 20),
                  ),
                ),
              ),
              const Positioned(
                left: 8,
                top: 8,
                child: _Tag(text: 'Before'),
              ),
              const Positioned(
                right: 8,
                top: 8,
                child: _Tag(text: 'After'),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _LeftClipper extends CustomClipper<Rect> {
  _LeftClipper(this.fraction);

  final double fraction;

  @override
  Rect getClip(Size size) => Rect.fromLTWH(0, 0, size.width * fraction, size.height);

  @override
  bool shouldReclip(covariant _LeftClipper old) => old.fraction != fraction;
}

class _Tag extends StatelessWidget {
  const _Tag({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.black54,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(text, style: const TextStyle(color: Colors.white, fontSize: 12)),
    );
  }
}
