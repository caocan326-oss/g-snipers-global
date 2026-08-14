from dataclasses import dataclass

from app.config import settings


@dataclass
class ProviderResult:
    sent: bool
    status: str
    detail: str


class ProviderAdapter:
    key: str
    label: str
    env_var: str = ""

    def configured(self) -> bool:
        return bool(self._api_key())

    def _api_key(self) -> str:
        return ""

    def send(self, *, title: str, target_url: str, payload_summary: str) -> ProviderResult:
        if not self.configured():
            return ProviderResult(sent=False, status="未配置", detail=f"{self.label} 未配置 API Key，未发送。")
        # Real HTTP is intentionally not implemented. Keys can exist later.
        return ProviderResult(
            sent=False,
            status="未实现",
            detail=f"{self.label} 已配置但本切片不发起真实第三方请求。",
        )


class DirectoryProvider(ProviderAdapter):
    key = "directory"
    label = "目录提交"
    env_var = "DISTRIBUTION_DIRECTORY_API_KEY"

    def _api_key(self) -> str:
        return settings.distribution_directory_api_key


class GuestNetworkProvider(ProviderAdapter):
    key = "guest_network"
    label = "客座网络"
    env_var = "DISTRIBUTION_GUEST_API_KEY"

    def _api_key(self) -> str:
        return settings.distribution_guest_api_key


class SyndicationProvider(ProviderAdapter):
    key = "syndication"
    label = "内容聚合"
    env_var = "DISTRIBUTION_SYNDICATION_API_KEY"

    def _api_key(self) -> str:
        return settings.distribution_syndication_api_key


_PROVIDERS: dict[str, ProviderAdapter] = {
    p.key: p
    for p in (DirectoryProvider(), GuestNetworkProvider(), SyndicationProvider())
}


def all_providers() -> list[ProviderAdapter]:
    return list(_PROVIDERS.values())


def get_provider(key: str) -> ProviderAdapter | None:
    return _PROVIDERS.get(key)
