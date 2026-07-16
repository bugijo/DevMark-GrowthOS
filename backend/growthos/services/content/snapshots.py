from growthos.models import BrandProfile, VisualPreset


def brand_snapshot(brand: BrandProfile | None) -> dict[str, object]:
    if brand is None:
        return {}
    return {
        "id": str(brand.id),
        "brand_name": brand.brand_name,
        "public_name": brand.public_name,
        "segment": brand.segment,
        "audience": brand.audience,
        "primary_colors": list(brand.primary_colors),
        "tone_of_voice": brand.tone_of_voice,
        "preferred_words": list(brand.preferred_words),
        "forbidden_words": list(brand.forbidden_words),
        "calls_to_action": list(brand.calls_to_action),
    }


def preset_snapshot(preset: VisualPreset | None) -> dict[str, object]:
    if preset is None:
        return {}
    return {
        "id": str(preset.id),
        "version": preset.version,
        "name": preset.name,
        "objective": preset.objective,
        "format": preset.format,
        "aspect_ratio": preset.aspect_ratio,
        "creation_mode": preset.creation_mode,
        "color_palette": list(preset.color_palette),
        "fonts": list(preset.fonts),
        "logo_media_asset_id": (
            str(preset.logo_media_asset_id) if preset.logo_media_asset_id else None
        ),
        "logo_position": preset.logo_position,
        "logo_scale_percent": preset.logo_scale_percent,
        "safe_margins": dict(preset.safe_margins),
        "background_style": preset.background_style,
        "photographic_style": preset.photographic_style,
        "realism_level": preset.realism_level,
        "lighting": preset.lighting,
        "composition": preset.composition,
        "max_text_characters": preset.max_text_characters,
        "text_rules": list(preset.text_rules),
        "base_prompt": preset.base_prompt,
        "negative_prompt": preset.negative_prompt,
        "allowed_elements": list(preset.allowed_elements),
        "forbidden_elements": list(preset.forbidden_elements),
        "visual_signature": preset.visual_signature,
        "default_cta": preset.default_cta,
    }
