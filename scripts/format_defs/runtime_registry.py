from formats import *  # noqa: F401,F403


@dataclass
class StubFormat(FormatBase):
    name: str


@dataclass
class StubVded(VdedBase):
    name: str


_FORMAT_REGISTRY: Dict[str, Callable[[], FormatBase]] = {}
_VDED_REGISTRY: Dict[str, Callable[[], VdedBase]] = {}


def register_format(name: str, factory: Callable[[], FormatBase]) -> None:
    _FORMAT_REGISTRY[name] = factory


def register_vded(name: str, factory: Callable[[], VdedBase]) -> None:
    _VDED_REGISTRY[name] = factory


def create_format(name: str) -> FormatBase:
    factory = _FORMAT_REGISTRY.get(name)
    if factory is not None:
        return factory()
    return BasicFormat(name=name)


def create_vded(name: str) -> VdedBase:
    factory = _VDED_REGISTRY.get(name)
    if factory is not None:
        return factory()
    return StubVded(name=name)
