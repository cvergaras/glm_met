"""Comparison plots for the SILO-corrected hourly source (needs matplotlib)."""

# Colorblind-validated series colors (adjacent-pair CVD-safe order)
COLOR_RAW = '#2a78d6'       # Open-Meteo / ERA5 raw
COLOR_SILO = '#eb6834'      # SILO daily reference
COLOR_ADJUSTED = '#1baf7a'  # adjusted output


def plot_silo_comparison(base, daily, adjusted, path):
    """Daily-aggregate comparison: raw Open-Meteo vs SILO vs adjusted output.

    Three panels sharing the time axis: rainfall totals, mean air temperature
    and mean shortwave. The adjusted line should sit on top of SILO's for all
    three — that overlap is the visual proof the correction worked.
    Returns True if the figure was written, False if matplotlib is missing.
    """
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print("[WARN] matplotlib is not installed; skipping plot. "
              "Install it with: pip install glm-met[plots]")
        return False

    def daily_agg(df):
        day = df['time'].dt.normalize()
        return df.groupby(day).agg(
            rain_mm=('Rain', lambda s: s.mean() * 1000),
            temp=('AirTemp', 'mean'),
            sw=('ShortWave', 'mean'),
        )

    om = daily_agg(base)
    adj = daily_agg(adjusted)

    fig, axes = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    panels = [
        ('rain_mm', 'rain_m', 1000.0, 'Rainfall (mm/day)'),
        ('temp', 'temp_mean', 1.0, 'Air temperature (°C)'),
        ('sw', 'rad_wm2', 1.0, 'Shortwave (W/m², daily mean)'),
    ]
    for ax, (om_col, silo_col, silo_scale, label) in zip(axes, panels):
        ax.plot(om.index, om[om_col], color=COLOR_RAW, lw=1.2,
                label='Open-Meteo (ERA5) raw')
        ax.plot(daily.index, daily[silo_col] * silo_scale, color=COLOR_SILO,
                lw=1.6, label='SILO daily')
        ax.plot(adj.index, adj[om_col], color=COLOR_ADJUSTED, lw=1.2,
                ls='--', label='glm-met output (adjusted)')
        ax.set_ylabel(label)
        ax.grid(True, alpha=0.25, lw=0.5)
        for spine in ('top', 'right'):
            ax.spines[spine].set_visible(False)
    axes[0].legend(loc='upper right', frameon=False, fontsize=9)
    axes[0].set_title('SILO correction of the Open-Meteo hourly base '
                      '(daily aggregates)', fontsize=11)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"[INFO] Comparison plot saved to {path}")
    return True
