
# -- Project information -----------------------------------------------------
import importlib.metadata

metadata = importlib.metadata.metadata("quiz")
project = metadata["Name"]
author = metadata["Author"]
version = metadata["Version"]

# -- General configuration ------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]
templates_path = ["_templates"]
source_suffix = ".rst"

master_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

pygments_style = 'sphinx'

# -- Options for HTML output ----------------------------------------------

autodoc_member_order = "bysource"
html_theme = "furo"
highlight_language = "python3"
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "gentools": ("https://gentools.readthedocs.io/en/latest/", None),
    "aiohttp": ("https://docs.aiohttp.org/en/latest/", None),
    "requests": ("https://requests.readthedocs.io/en/latest/", None),
}
