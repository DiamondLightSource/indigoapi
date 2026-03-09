import importlib
import logging
import pkgutil
from pathlib import Path

from git import Repo

from indigoapi.config import Config

logger = logging.getLogger(__name__)


def load_analyses(package):

    module_names = []

    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        importlib.import_module(f"{package.__name__}.{module_name}")
        module_names.append(module_name)

    return module_names


def load_plugins_from_dir(path: str | Path):
    """Load user plugins from a folder"""
    path = Path(path)
    assert isinstance(path, Path)
    if not path.exists():
        return
    for pyfile in path.glob("*.py"):
        spec = importlib.util.spec_from_file_location(pyfile.stem, pyfile)  # type: ignore
        module = importlib.util.module_from_spec(spec)  # type: ignore
        spec.loader.exec_module(module)


def clone_github_repo(repo_url: str, dest_dir: str):
    """Clone a repo if not already cloned"""
    dest_path = Path(dest_dir) / Path(repo_url).stem
    if dest_path.exists():
        return dest_path

    Repo.clone_from(repo_url, dest_path)

    return dest_path


def load_plugins(config: Config):
    """Load all user plugins (local + GitHub)"""
    # Local paths
    for p in config.plugins.paths:
        load_plugins_from_dir(p)

    # GitHub repos
    if config.plugins.github_repos is not None:
        for repo in config.plugins.github_repos:
            try:
                repo_path = clone_github_repo(repo, "./plugins")  # cloned into plugins/
                load_plugins_from_dir(repo_path)
            except Exception as e:
                logger.error(f"Unable to load {repo}: {e}")
