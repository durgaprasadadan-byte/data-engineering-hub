"""Generate bundled SYNTHETIC sample data into data/sample/<project>/. Run: python -m scripts.generate_sample_data"""
from src.config.settings import SETTINGS
from src.data_gen.synthetic import GENERATORS


def main() -> None:
    for project, gen in GENERATORS.items():
        out = SETTINGS.sample_dir / project
        out.mkdir(parents=True, exist_ok=True)
        for name, df in gen().items():
            if project == "ecommerce" and name == "inventory":       # demonstrates JSON ingestion
                df.to_json(out / f"{name}.json", orient="records", indent=1)
            else:
                df.to_csv(out / f"{name}.csv", index=False)
        print(f"wrote {project}: {sorted(p.name for p in out.iterdir())}")


if __name__ == "__main__":
    main()
