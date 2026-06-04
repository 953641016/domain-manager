import pytest

from app.adapters.registrar_factory import RegistrarFactory
from app.api.v1.registrar import HIDDEN_REGISTRAR_CODES


def test_current_supported_registrars_exclude_placeholder_providers():
    assert RegistrarFactory.SUPPORTED_REGISTRARS == ["cloudflare", "godaddy"]
    assert HIDDEN_REGISTRAR_CODES == {"namecheap", "enom"}


@pytest.mark.parametrize("code", ["namecheap", "enom"])
def test_placeholder_registrars_are_not_creatable(code):
    with pytest.raises(ValueError) as exc:
        RegistrarFactory.create_registrar(code=code, api_key="key")

    assert "不支持的注册商" in str(exc.value)
