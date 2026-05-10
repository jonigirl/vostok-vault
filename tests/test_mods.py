from pathlib import Path

from vostok_vault.mods import get_mod_names, parse_mod_config

MOD_CONFIG_CFG = """\
[settings]
developer_mode=false
active_profile="Default"

[profile.Default.enabled]
doinkoink-mcm@2.7.0=true
elegant-hud@1.0.2=true
feel@0.0.2=false
"""


def test_parse_mod_config_missing_file(tmp_path: Path) -> None:
    mods, profile = parse_mod_config(tmp_path / "missing.cfg")
    assert mods == []
    assert profile == ""


def test_parse_mod_config_returns_three_mods(tmp_path: Path) -> None:
    p = tmp_path / "mod_config.cfg"
    p.write_text(MOD_CONFIG_CFG, encoding="utf-8")
    mods, _ = parse_mod_config(p)
    assert len(mods) == 3


def test_parse_mod_config_ids(tmp_path: Path) -> None:
    p = tmp_path / "mod_config.cfg"
    p.write_text(MOD_CONFIG_CFG, encoding="utf-8")
    mods, _ = parse_mod_config(p)
    assert {m["id"] for m in mods} == {"doinkoink-mcm", "elegant-hud", "feel"}


def test_parse_mod_config_versions(tmp_path: Path) -> None:
    p = tmp_path / "mod_config.cfg"
    p.write_text(MOD_CONFIG_CFG, encoding="utf-8")
    mods, _ = parse_mod_config(p)
    versions = {m["id"]: m["version"] for m in mods}
    assert versions["doinkoink-mcm"] == "2.7.0"
    assert versions["elegant-hud"] == "1.0.2"
    assert versions["feel"] == "0.0.2"


def test_parse_mod_config_enabled_flags(tmp_path: Path) -> None:
    p = tmp_path / "mod_config.cfg"
    p.write_text(MOD_CONFIG_CFG, encoding="utf-8")
    mods, _ = parse_mod_config(p)
    enabled = {m["id"]: m["enabled"] for m in mods}
    assert enabled["doinkoink-mcm"] is True
    assert enabled["elegant-hud"] is True
    assert enabled["feel"] is False


def test_parse_mod_config_no_enabled_section(tmp_path: Path) -> None:
    p = tmp_path / "mod_config.cfg"
    p.write_text("[settings]\nfoo=bar\n", encoding="utf-8")
    mods, profile = parse_mod_config(p)
    assert mods == []
    assert profile == ""


def test_parse_mod_config_active_profile(tmp_path: Path) -> None:
    p = tmp_path / "mod_config.cfg"
    p.write_text(MOD_CONFIG_CFG, encoding="utf-8")
    _, profile = parse_mod_config(p)
    assert profile == "Default"


def test_parse_mod_config_skips_keys_without_at(tmp_path: Path) -> None:
    content = "[profile.Default.enabled]\nno-at-sign=true\nmod@1.0.0=true\n"
    p = tmp_path / "mod_config.cfg"
    p.write_text(content, encoding="utf-8")
    mods, _ = parse_mod_config(p)
    assert len(mods) == 1
    assert mods[0]["id"] == "mod"


def test_get_mod_names_no_pass_state(tmp_path: Path) -> None:
    assert get_mod_names(tmp_path) == {}


def test_get_mod_names_empty_pass_state(tmp_path: Path) -> None:
    (tmp_path / "mod_pass_state.cfg").write_text("[paths]\n", encoding="utf-8")
    assert get_mod_names(tmp_path) == {}


def test_get_mod_names_pass_state_no_vmz_paths(tmp_path: Path) -> None:
    content = "[archive_paths]\n"
    (tmp_path / "mod_pass_state.cfg").write_text(content, encoding="utf-8")
    assert get_mod_names(tmp_path) == {}
