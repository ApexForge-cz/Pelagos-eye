from oceanscope_api.core.settings import Settings


def test_cors_origins_are_parsed_without_blank_values() -> None:
    settings = Settings(cors_origins="https://one.example, ,https://two.example")

    assert settings.cors_origin_list == ["https://one.example", "https://two.example"]


def test_blank_public_url_is_treated_as_unset() -> None:
    settings = Settings(public_base_url="   ")

    assert settings.public_base_url is None


def test_live_ais_origins_are_separate_from_cors() -> None:
    settings = Settings(
        cors_origins="https://api.example",
        live_ais_origins="http://localhost:5173, ,http://127.0.0.1:5173",
    )

    assert settings.cors_origin_list == ["https://api.example"]
    assert settings.live_ais_origin_list == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_blank_pelyr_key_keeps_optional_worker_disabled() -> None:
    settings = Settings.model_validate({"PELYR_API_KEY": "   "})

    assert settings.pelyr_api_key is None
