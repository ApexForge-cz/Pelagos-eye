from oceanscope_api.core.settings import Settings


def test_cors_origins_are_parsed_without_blank_values() -> None:
    settings = Settings(cors_origins="https://one.example, ,https://two.example")

    assert settings.cors_origin_list == ["https://one.example", "https://two.example"]


def test_blank_public_url_is_treated_as_unset() -> None:
    settings = Settings(public_base_url="   ")

    assert settings.public_base_url is None
