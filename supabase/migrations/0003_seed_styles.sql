-- Seed the four launch styles with prompt templates from architecture §5.2.
-- The {style} placeholder in prompt_template is filled by the prompt builder
-- (app/ml/prompts.py); these templates are the fuller per-style versions.

insert into styles (name, name_ru, prompt_template, is_premium, sort_order) values
  (
    'Natural White', 'Естественный белый',
    'Beautiful naturally white teeth, slight improvement in alignment, same lip shape and skin tone, photorealistic, maintain original lighting and shadows',
    false, 1
  ),
  (
    'Straight Smile', 'Ровная улыбка',
    'Perfectly aligned straight teeth, natural white shade, no gaps, same lip shape, photorealistic dental result, maintain skin texture',
    false, 2
  ),
  (
    'Veneer Effect', 'Эффект виниров',
    'Professional dental veneer result, uniform tooth shape and size, bright white but natural-looking, celebrity-quality smile, same lip contour',
    true, 3
  ),
  (
    'Hollywood Smile', 'Голливудская улыбка',
    'Brilliant white Hollywood smile, perfect symmetry, gleaming teeth, red carpet ready, maintain natural lip shape and facial features',
    true, 4
  );
