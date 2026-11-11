"""Write .mmd and .dot files for every architecture into diagrams/."""
from src.config.settings import SETTINGS
from src.diagrams.definitions import ARCHITECTURES, to_dot, to_mermaid

SETTINGS.diagrams_dir.mkdir(exist_ok=True)
for key, arch in ARCHITECTURES.items():
    (SETTINGS.diagrams_dir / f"{key}_architecture.mmd").write_text(to_mermaid(arch))
    (SETTINGS.diagrams_dir / f"{key}_architecture.dot").write_text(to_dot(arch))
    print("wrote", key)
