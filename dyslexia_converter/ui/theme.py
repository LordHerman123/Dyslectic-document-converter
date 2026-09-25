"""App colours: a warm autumn palette (cream, sand, caramel, terracotta) with a dark 'espresso' variant.

Only the app's own screens use these. Exported documents keep their own colours (settings.py).
"""
from __future__ import annotations

import flet as ft

LIGHT = {
    "bg": "#F5EFE6",            # cream
    "surface": "#FBF7F1",
    "surface_low": "#F2EADF",
    "surface_mid": "#ECE1D3",
    "surface_high": "#E4D6C4",  # sand
    "text": "#4A3328",          # dark brown
    "muted": "#7A5E4E",
    "primary": "#A0654E",       # terracotta
    "on_primary": "#FFFFFF",
    "primary_container": "#EBD3C6",
    "on_primary_container": "#4A2A1E",
    "secondary": "#C9953F",     # caramel / mustard
    "on_secondary": "#33230A",
    "secondary_container": "#F1DDB5",
    "on_secondary_container": "#4A3510",
    "tertiary": "#8C7A68",      # taupe
    "on_tertiary": "#FFFFFF",
    "outline": "#B39C88",
    "outline_variant": "#DCCDBB",
    "notice_warning": "#F3DDB0",
    "notice_action": "#EBD3C6",
    "notice_info": "#E8DFD2",
    "chip_local": "#DFE2CB",    # soft sage
    "chip_ai": "#F1DDB5",
    "frame": "#33000000",
}

DARK = {
    "bg": "#231B17",            # espresso
    "surface": "#2B221D",
    "surface_low": "#2F2520",
    "surface_mid": "#362B25",
    "surface_high": "#40332B",
    "text": "#F0E6DA",
    "muted": "#CDB9A7",
    "primary": "#E0A882",       # light terracotta
    "on_primary": "#3A1F14",
    "primary_container": "#6E4636",
    "on_primary_container": "#F6DDD0",
    "secondary": "#DDB36A",     # caramel
    "on_secondary": "#33250C",
    "secondary_container": "#5A4420",
    "on_secondary_container": "#F5E3BF",
    "tertiary": "#C4B3A1",
    "on_tertiary": "#2E241D",
    "outline": "#8D7A6B",
    "outline_variant": "#4E3F36",
    "notice_warning": "#4F3E1E",
    "notice_action": "#553729",
    "notice_info": "#3A302A",
    "chip_local": "#3D4230",
    "chip_ai": "#5A4420",
    "frame": "#44FFFFFF",
}

# high contrast: plain white/black with a strong brown accent
HC_LIGHT = {**LIGHT, "bg": "#FFFFFF", "surface": "#FFFFFF", "surface_low": "#FFFFFF", "surface_mid": "#F4F4F4",
            "surface_high": "#EAEAEA", "text": "#000000", "muted": "#222222", "primary": "#5A2E1E",
            "outline": "#000000", "outline_variant": "#555555", "frame": "#FF000000"}
HC_DARK = {**DARK, "bg": "#000000", "surface": "#000000", "surface_low": "#000000", "surface_mid": "#141414",
           "surface_high": "#202020", "text": "#FFFFFF", "muted": "#EEEEEE", "primary": "#F2C29A",
           "outline": "#FFFFFF", "outline_variant": "#AAAAAA", "frame": "#FFFFFFFF"}


def palette(dark: bool, high_contrast: bool = False) -> dict[str, str]:
    if high_contrast:
        return HC_DARK if dark else HC_LIGHT
    return DARK if dark else LIGHT


def make_theme(pal: dict[str, str], font_family: str) -> ft.Theme:
    scheme = ft.ColorScheme(
        primary=pal["primary"], on_primary=pal["on_primary"],
        primary_container=pal["primary_container"], on_primary_container=pal["on_primary_container"],
        secondary=pal["secondary"], on_secondary=pal["on_secondary"],
        secondary_container=pal["secondary_container"], on_secondary_container=pal["on_secondary_container"],
        tertiary=pal["tertiary"], on_tertiary=pal["on_tertiary"],
        surface=pal["surface"], on_surface=pal["text"], on_surface_variant=pal["muted"],
        surface_container_lowest=pal["surface"], surface_container_low=pal["surface_low"],
        surface_container=pal["surface_mid"], surface_container_high=pal["surface_high"],
        surface_container_highest=pal["surface_high"], surface_tint=pal["primary"],
        outline=pal["outline"], outline_variant=pal["outline_variant"],
    )
    return ft.Theme(color_scheme=scheme, font_family=font_family, scaffold_bgcolor=pal["bg"],
                    divider_color=pal["outline_variant"])
