from pathlib import Path

from vostok_vault.mcm_parser import _parse_mcm_config, parse_mcm_configs

_SAMPLE_CONFIG = """\
[Bool]

hide_inactive={
&"category": "Conditions",
&"default": true,
&"menu_pos": 1,
&"name": "Hide Inactive Icons",
&"tooltip": "Whether inactive icons should be hidden.",
&"value": true
}
show_reticle={
&"category": "Reticle",
&"default": false,
&"menu_pos": 2,
&"name": "Enable Reticle",
&"tooltip": "Show a reticle.",
&"value": false
}

[Float]

vitals_scale={
&"category": "Scale",
&"default": 1.0,
&"maxRange": 5.0,
&"menu_pos": 1,
&"minRange": 0.1,
&"name": "Vitals Scale",
&"tooltip": "Set the scale.",
&"value": 0.85
}

[Int]

max_items={
&"default": 10,
&"menu_pos": 1,
&"name": "Max Items",
&"tooltip": "Maximum items.",
&"value": 15
}

[Color]

color_health={
&"default": Color(0.87, 0.54, 0.54, 1),
&"menu_pos": 1,
&"name": "Health Color",
&"tooltip": "Health bar color.",
&"value": Color(1, 0, 0, 1)
}

[Keycode]

toggle_key={
&"default": 79,
&"menu_pos": 1,
&"name": "Toggle Key",
&"tooltip": "Toggle key.",
&"value": 79
}
"""


def _write_mod_config(tmp_path: Path, mod_id: str, content: str) -> Path:
    mod_dir = tmp_path / "MCM" / mod_id
    mod_dir.mkdir(parents=True)
    cfg = mod_dir / "config.ini"
    cfg.write_text(content, encoding="utf-8")
    return tmp_path


def test_parse_mcm_configs_empty_dir(tmp_path: Path) -> None:
    result = parse_mcm_configs(tmp_path / "MCM")
    assert result == {}


def test_parse_mcm_configs_missing_dir(tmp_path: Path) -> None:
    result = parse_mcm_configs(tmp_path / "nonexistent" / "MCM")
    assert result == {}


def test_parse_mcm_configs_returns_mod_entry(tmp_path: Path) -> None:
    _write_mod_config(tmp_path, "TestMod", _SAMPLE_CONFIG)
    result = parse_mcm_configs(tmp_path / "MCM")
    assert "TestMod" in result


def test_parse_mcm_configs_skips_dir_without_config(tmp_path: Path) -> None:
    (tmp_path / "MCM" / "EmptyMod").mkdir(parents=True)
    result = parse_mcm_configs(tmp_path / "MCM")
    assert result == {}


def test_parse_mcm_config_setting_count(tmp_path: Path) -> None:
    cfg = tmp_path / "config.ini"
    cfg.write_text(_SAMPLE_CONFIG, encoding="utf-8")
    settings = _parse_mcm_config(cfg)
    assert len(settings) == 6


def test_parse_mcm_config_bool_on(tmp_path: Path) -> None:
    cfg = tmp_path / "config.ini"
    cfg.write_text(_SAMPLE_CONFIG, encoding="utf-8")
    settings = _parse_mcm_config(cfg)
    hide = next(s for s in settings if s["key"] == "hide_inactive")
    assert hide["display_value"] == "On"
    assert hide["name"] == "Hide Inactive Icons"
    assert hide["type"] == "Bool"


def test_parse_mcm_config_bool_off(tmp_path: Path) -> None:
    cfg = tmp_path / "config.ini"
    cfg.write_text(_SAMPLE_CONFIG, encoding="utf-8")
    settings = _parse_mcm_config(cfg)
    reticle = next(s for s in settings if s["key"] == "show_reticle")
    assert reticle["display_value"] == "Off"


def test_parse_mcm_config_float_value(tmp_path: Path) -> None:
    cfg = tmp_path / "config.ini"
    cfg.write_text(_SAMPLE_CONFIG, encoding="utf-8")
    settings = _parse_mcm_config(cfg)
    scale = next(s for s in settings if s["key"] == "vitals_scale")
    assert scale["display_value"] == "0.85"
    assert scale["type"] == "Float"


def test_parse_mcm_config_int_value(tmp_path: Path) -> None:
    cfg = tmp_path / "config.ini"
    cfg.write_text(_SAMPLE_CONFIG, encoding="utf-8")
    settings = _parse_mcm_config(cfg)
    items = next(s for s in settings if s["key"] == "max_items")
    assert items["display_value"] == "15"


def test_parse_mcm_config_color_value(tmp_path: Path) -> None:
    cfg = tmp_path / "config.ini"
    cfg.write_text(_SAMPLE_CONFIG, encoding="utf-8")
    settings = _parse_mcm_config(cfg)
    color = next(s for s in settings if s["key"] == "color_health")
    assert "Color" in color["display_value"]


def test_parse_mcm_config_keycode_value(tmp_path: Path) -> None:
    cfg = tmp_path / "config.ini"
    cfg.write_text(_SAMPLE_CONFIG, encoding="utf-8")
    settings = _parse_mcm_config(cfg)
    key = next(s for s in settings if s["key"] == "toggle_key")
    assert key["display_value"].startswith("Key ")


def test_parse_mcm_config_sorted_by_category_then_menu_pos(tmp_path: Path) -> None:
    cfg = tmp_path / "config.ini"
    cfg.write_text(_SAMPLE_CONFIG, encoding="utf-8")
    settings = _parse_mcm_config(cfg)
    # Settings without a category (Int, Keycode, Color in sample) sort first under ""
    # Then alphabetical by category name
    categories = [s["category"] for s in settings]
    assert categories == sorted(categories)


def test_parse_mcm_config_category_field(tmp_path: Path) -> None:
    cfg = tmp_path / "config.ini"
    cfg.write_text(_SAMPLE_CONFIG, encoding="utf-8")
    settings = _parse_mcm_config(cfg)
    hide = next(s for s in settings if s["key"] == "hide_inactive")
    assert hide["category"] == "Conditions"


def test_parse_mcm_config_ignores_category_section(tmp_path: Path) -> None:
    content = """\
[Category]

MyCategory={
&"menu_pos": 1,
&"name": "My Category"
}

[Bool]

my_bool={
&"name": "My Bool",
&"default": true,
&"value": false
}
"""
    cfg = tmp_path / "config.ini"
    cfg.write_text(content, encoding="utf-8")
    settings = _parse_mcm_config(cfg)
    assert len(settings) == 1
    assert settings[0]["key"] == "my_bool"
