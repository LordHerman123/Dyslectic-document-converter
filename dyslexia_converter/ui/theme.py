"""App colours: burgundy & champagne on warm cream, with a dark 'wine' variant (matches the logo).

Only the app's own screens use these. Exported documents keep their own colours (settings.py).
"""
from __future__ import annotations

import flet as ft

LIGHT = {
    "bg": "#FBF6EE",            # warm cream
    "surface": "#FFFCF7",
    "surface_low": "#F7EFE4",
    "surface_mid": "#F1E6D7",
    "surface_high": "#E9DAC6",  # champagne sand
    "text": "#3F1A21",          # deep burgundy-brown
    "muted": "#7A5058",
    "primary": "#7A2E3A",       # burgundy
    "on_primary": "#FFFFFF",
    "primary_container": "#F0D9DC",
    "on_primary_container": "#4A1C24",
    "secondary": "#C9A15A",     # champagne gold
    "on_secondary": "#2E2210",
    "secondary_container": "#F2E3C4",
    "on_secondary_container": "#4A3814",
    "tertiary": "#8C6B5E",
    "on_tertiary": "#FFFFFF",
    "outline": "#B99A8E",
    "outline_variant": "#E3D3C3",
    "notice_warning": "#F2E3C4",
    "notice_action": "#F0D9DC",
    "notice_info": "#EFE6DA",
    "chip_local": "#E4E7D3",    # soft sage
    "chip_ai": "#F2E3C4",
    "status_local": "#4F7A4B",  # green lock: nothing leaves the device
    "status_ai": "#A0782E",
    "frame": "#33000000",
}

DARK = {
    "bg": "#1F1517",            # dark wine
    "surface": "#271B1E",
    "surface_low": "#2C1F22",
    "surface_mid": "#342528",
    "surface_high": "#3E2D31",
    "text": "#F3E7DC",
    "muted": "#D2BCB2",
    "primary": "#E3A3AE",       # soft rose
    "on_primary": "#4A1C24",
    "primary_container": "#6B2733",
    "on_primary_container": "#F8DDE1",
    "secondary": "#E2C48A",     # champagne
    "on_secondary": "#33260E",
    "secondary_container": "#5A4620",
    "on_secondary_container": "#F5E6C4",
    "tertiary": "#C9ADA2",
    "on_tertiary": "#2E2020",
    "outline": "#8E747A",
    "outline_variant": "#4F3A3F",
    "notice_warning": "#4F3F1E",
    "notice_action": "#5A2A33",
    "notice_info": "#3A2C2F",
    "chip_local": "#3B402E",
    "chip_ai": "#5A4620",
    "status_local": "#A9C9A0",
    "status_ai": "#E2C48A",
    "frame": "#44FFFFFF",
}

# high contrast: plain white/black with a strong burgundy accent
HC_LIGHT = {**LIGHT, "bg": "#FFFFFF", "surface": "#FFFFFF", "surface_low": "#FFFFFF", "surface_mid": "#F4F4F4",
            "surface_high": "#EAEAEA", "text": "#000000", "muted": "#222222", "primary": "#6B1F2B",
            "outline": "#000000", "outline_variant": "#555555", "frame": "#FF000000"}
HC_DARK = {**DARK, "bg": "#000000", "surface": "#000000", "surface_low": "#000000", "surface_mid": "#141414",
           "surface_high": "#202020", "text": "#FFFFFF", "muted": "#EEEEEE", "primary": "#F2B8C2",
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
