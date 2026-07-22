def get_source(name, **options):
    """Return a MetSource instance by name ('openmeteo', 'silo' or 'gee')."""
    if name == 'openmeteo':
        from .openmeteo import OpenMeteoSource
        return OpenMeteoSource(model=options.get('model', 'best_match'))
    if name == 'silo':
        from .silo import SiloSource
        return SiloSource(email=options.get('email'),
                          model=options.get('model', 'best_match'))
    if name == 'gee':
        try:
            import ee  # noqa: F401
        except ImportError:
            raise SystemExit(
                "The 'gee' source needs the earthengine-api package.\n"
                "Install it with: pip install glm-met[gee]"
            )
        from .gee import GEESource
        return GEESource(project=options.get('project'))
    raise ValueError(f"Unknown source: {name!r}")
